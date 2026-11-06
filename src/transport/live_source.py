"""Receive-only helper, historical replay, and clearly labeled synthetic input."""
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import threading
import time

from .duml_observer import crc8, crc16


def parse_helper_line(line):
    if not isinstance(line, str) or len(line) > 131072:
        raise ValueError('Oversized or invalid helper line')
    try:
        event = json.loads(line)
    except (ValueError, TypeError) as error:
        raise ValueError('Malformed helper JSON') from error
    if not isinstance(event, dict) or event.get('type') not in ('ready', 'transfer', 'error', 'end'):
        raise ValueError('Unknown helper event')
    if event['type'] in ('ready', 'transfer'):
        if event.get('interface') != 4 or event.get('endpoint_in') != '0x85':
            raise ValueError('Unexpected helper endpoint')
    if event['type'] == 'ready' and event.get('read_only') is not True:
        raise ValueError('Helper did not declare receive-only operation')
    if event['type'] == 'transfer':
        encoded = event.get('hex')
        if not isinstance(encoded, str) or len(encoded) > 32768 or len(encoded) % 2:
            raise ValueError('Invalid transfer hex length')
        try:
            data = bytes.fromhex(encoded)
        except ValueError as error:
            raise ValueError('Invalid transfer hex') from error
        if event.get('bytes') != len(data):
            raise ValueError('Transfer length mismatch')
        event['data'] = data
    if event['type'] == 'end' and event.get('application_bytes_sent', 0) != 0:
        raise ValueError('Helper violated receive-only declaration')
    return event


class _ThreadSource:
    def __init__(self, state):
        self.state = state
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None:
            raise RuntimeError('A source can only be started once')
        self._thread = threading.Thread(target=self._run_guarded, daemon=True,
                                        name='neo2-' + self.state.mode)
        self._thread.start()
        return self

    def _run_guarded(self):
        try:
            self._run()
        except Exception as error:
            self.state.set_error(f'{type(error).__name__}: {error}')
        finally:
            self.state.end('Source stopped')

    def stop(self):
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)


class LiveSource(_ThreadSource):
    def __init__(self, state, helper_path):
        if state.mode != 'live':
            raise ValueError('LiveSource requires mode=live')
        super().__init__(state)
        self.helper_path = Path(helper_path).resolve()
        self._process = None
        self._process_lock = threading.Lock()

    def _run(self):
        if self._stop.is_set():
            return
        # No shell, arbitrary arguments, packet encoder, or writes to child stdin.
        process = subprocess.Popen([str(self.helper_path), '--receive-only'],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1,
                                   env={**os.environ, 'LIBUSB_DEBUG': '0'})
        with self._process_lock:
            self._process = process
        try:
            while not self._stop.is_set():
                line = process.stdout.readline(131073)
                if not line:
                    break
                event = parse_helper_line(line)
                kind = event['type']
                if kind == 'ready':
                    self.state.set_ready()
                elif kind == 'transfer':
                    self.state.ingest(event['data'])
                elif kind == 'error':
                    self.state.set_error('USB ' + str(event.get('stage', 'unknown')) +
                                         ': ' + str(event.get('code', 'unknown')))
                elif kind == 'end':
                    if event.get('exit_code', 0) and not self._stop.is_set():
                        self.state.set_error('USB helper exited: ' + str(event['exit_code']))
                    break
            code = process.poll()
            if code not in (None, 0) and not self._stop.is_set():
                self.state.set_error('USB helper exited: ' + str(code))
        finally:
            self._terminate(process)
            if process.stdout:
                process.stdout.close()

    @staticmethod
    def _terminate(process):
        if process.poll() is None:
            try:
                process.terminate()
            except ProcessLookupError:
                return
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)

    def stop(self):
        self._stop.set()
        with self._process_lock:
            if self._process is not None:
                self._terminate(self._process)
        super().stop()


def replay_chunks(path):
    path = Path(path)
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError('Replay capture exceeds 32 MiB bound')
    capture = json.loads(path.read_text())
    chunks = []
    if 'observations' in capture:
        for observation in capture['observations']:
            if observation.get('interface') != 4:
                continue
            for chunk in observation.get('chunks', []):
                data = bytes.fromhex(chunk['hex'])
                offset = chunk.get('offset_ms')
                if offset is not None and (type(offset) not in (int, float) or
                                            not math.isfinite(offset) or offset < 0):
                    raise ValueError('Invalid replay offset')
                chunks.append((offset, data))
    else:
        for field in ('preflight_rx_hex', 'response_rx_hex'):
            if field in capture:
                data = bytes.fromhex(capture[field])
                chunks.extend((None, data[i:i + 512]) for i in range(0, len(data), 512))
    if not chunks:
        raise ValueError('Capture has no interface-4 replay data')
    return chunks


class ReplaySource(_ThreadSource):
    def __init__(self, state, capture_path, *, speed=1.0, loop=True):
        if state.mode != 'replay':
            raise ValueError('ReplaySource requires mode=replay')
        if not math.isfinite(speed) or not 0.1 <= speed <= 10:
            raise ValueError('Replay speed must be between 0.1 and 10')
        super().__init__(state)
        self.capture_path = Path(capture_path)
        self.speed = speed
        self.loop = bool(loop)

    def _run(self):
        chunks = replay_chunks(self.capture_path)
        self.state.set_source_detail('Historical capture replay; saved transfer offsets or 20 ms fallback pacing')
        self.state.set_ready()
        while not self._stop.is_set():
            previous = None
            for offset, data in chunks:
                delay = 0.02 if offset is None or previous is None else min(1.0, max(0.0, (offset - previous) / 1000))
                if self._stop.wait(delay / self.speed):
                    return
                self.state.ingest(data)
                previous = offset
            if not self.loop or self._stop.wait(0.1):
                return


def _synthetic_packet(sender, receiver, command, sequence, payload):
    length = 13 + len(payload)
    raw = bytearray([0x55, length & 255, 4 | (length >> 8), 0,
                     sender, receiver, sequence & 255, sequence >> 8,
                     0, command[0], command[1]])
    raw[3] = crc8(raw[:3])
    raw.extend(payload)
    raw.extend(crc16(raw).to_bytes(2, 'little'))
    return bytes(raw)


class DemoSource(_ThreadSource):
    def __init__(self, state):
        if state.mode != 'demo':
            raise ValueError('DemoSource requires mode=demo')
        super().__init__(state)

    def _run(self):
        self.state.set_source_detail('Synthetic demonstration; no aircraft connected or queried')
        self.state.set_ready()
        started = time.monotonic()
        sequence = 0
        while not self._stop.is_set():
            elapsed = time.monotonic() - started
            a, b, c = 8 * math.sin(elapsed * 0.7), 12 * math.sin(elapsed * 0.4), (elapsed * 12) % 360 - 180
            aircraft = bytearray(85)
            struct.pack_into('<hhh', aircraft, 24, round(a * 10), round(b * 10), round(c * 10))
            gimbal = bytearray(50)
            struct.pack_into('<hhh', gimbal, 0, round(-a * 2), 0, round(c * 10))
            yaw = math.radians(c) / 2
            struct.pack_into('<ffff', gimbal, 24, math.cos(yaw), 0, 0, math.sin(yaw))
            self.state.ingest(_synthetic_packet(3, 10, (3, 0x43), sequence, aircraft) +
                              _synthetic_packet(4, 42, (4, 5), sequence, gimbal))
            sequence = (sequence + 1) & 65535
            self._stop.wait(0.02)
