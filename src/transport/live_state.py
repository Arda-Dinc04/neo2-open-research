"""Thread-safe state for an observation-only aircraft/gimbal viewer."""
from collections import deque
import copy
import math
import threading
import time

from .component_observer import fc_fields, gimbal_fields
from .duml_observer import Stream


class LiveState:
    def __init__(self, mode='live', *, clock=time.monotonic, stale_after=1.0,
                 history_limit=1800):
        if mode not in ('live', 'replay', 'demo'):
            raise ValueError('Unknown source mode')
        if not 0 < stale_after <= 60 or history_limit < 1:
            raise ValueError('Invalid state bounds')
        self.mode = mode
        self.clock = clock
        self.stale_after = float(stale_after)
        self._lock = threading.RLock()
        self._started = float(clock())
        if not math.isfinite(self._started):
            raise ValueError('Nonfinite start timestamp')
        self._stream = Stream()
        self._last_ingest = None
        self._last_frame = None
        self._last_orientation = None
        self._aircraft = None
        self._gimbal = None
        self._ended = False
        self._ready = False
        self._error = None
        self._source_detail = None
        self._frames = 0
        self._bytes = 0
        self._rejected = 0
        self._encrypted = 0
        self._frame_times = deque(maxlen=10000)
        self._history = deque(maxlen=history_limit)

    def set_ready(self):
        with self._lock:
            self._ready = True
            self._ended = False
            self._error = None

    def set_source_detail(self, detail):
        with self._lock:
            self._source_detail = str(detail)[:300]

    def set_error(self, message):
        with self._lock:
            self._error = str(message)[:500]

    def end(self, reason=None):
        with self._lock:
            self._ended = True
            if reason and not self._error:
                self._source_detail = str(reason)[:300]

    @staticmethod
    def _source(frame):
        return {'sender': f'{frame.sender:02x}', 'receiver': f'{frame.receiver:02x}',
                'command': f'{frame.command[0]:02x}/{frame.command[1]:02x}',
                'sequence': frame.sequence}

    def ingest(self, data, timestamp=None):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError('Expected received bytes')
        if len(data) > 1024 * 1024:
            raise ValueError('Oversized receive chunk')
        received_at = float(self.clock() if timestamp is None else timestamp)
        if not math.isfinite(received_at):
            raise ValueError('Nonfinite receipt timestamp')
        with self._lock:
            if self._last_ingest is not None and received_at < self._last_ingest:
                raise ValueError('Receipt time moved backwards')
            self._last_ingest = received_at
            self._bytes += len(data)
            frames = self._stream.feed(data)
            self._frames += len(frames)
            updated = False
            for frame in frames:
                self._last_frame = received_at
                self._frame_times.append(received_at)
                if frame.raw[8] & 7:
                    self._encrypted += 1
                    continue
                try:
                    if frame.sender == 3 and frame.command == (3, 0x43):
                        fields = fc_fields(frame.payload)
                        self._aircraft = {
                            'angles_deg': fields['attitude_degrees_sdk_order'],
                            'raw': fields['attitude_tenths_raw'],
                            'source': self._source(frame),
                            'received_at': received_at,
                            'axes_verified': False,
                        }
                        self._history.append({'timestamp': received_at,
                                              'kind': 'aircraft',
                                              'angles_deg': list(self._aircraft['angles_deg']),
                                              'source': self._source(frame)})
                        updated = True
                    elif frame.sender == 4 and frame.command == (4, 5):
                        fields = gimbal_fields(frame.payload)
                        self._gimbal = {
                            'angles_deg': fields['angles_degrees_sdk_order'],
                            'raw': fields['angles_tenths_raw'],
                            'quaternion': fields['quaternion_fields_sdk_order'],
                            'quaternion_norm': fields['quaternion_norm'],
                            'source': self._source(frame),
                            'received_at': received_at,
                            'axes_verified': False,
                        }
                        self._history.append({'timestamp': received_at,
                                              'kind': 'gimbal',
                                              'angles_deg': list(self._gimbal['angles_deg']),
                                              'source': self._source(frame)})
                        updated = True
                except ValueError:
                    self._rejected += 1
            if updated:
                self._last_orientation = received_at
                self._ended = False
            return len(frames)

    def history_snapshot(self, since=None):
        with self._lock:
            return copy.deepcopy([item for item in self._history
                                  if since is None or item['timestamp'] >= since])

    def snapshot(self, now=None):
        current = float(self.clock() if now is None else now)
        if not math.isfinite(current):
            raise ValueError('Nonfinite snapshot timestamp')
        with self._lock:
            while self._frame_times and self._frame_times[0] < current - 1.0:
                self._frame_times.popleft()
            age = None if self._last_orientation is None else max(0.0, current - self._last_orientation)
            if self._error:
                status = 'error'
            elif self._ended:
                status = 'disconnected'
            elif age is None:
                status = 'starting'
            elif age > self.stale_after:
                status = 'stale'
            else:
                status = 'streaming'
            def channel(value):
                if value is None:
                    return None
                result = copy.deepcopy(value)
                result['age_ms'] = round(max(0.0, current - value['received_at']) * 1000, 1)
                result['stale'] = result['age_ms'] > self.stale_after * 1000
                return result
            return {
                'mode': self.mode, 'status': status,
                'age_ms': None if age is None else round(age * 1000, 1),
                'uptime_s': round(max(0.0, current - self._started), 2),
                'transport': {
                    'interface': 4, 'endpoint_in': '0x85', 'ready': self._ready,
                    'frames_total': self._frames, 'bytes_received': self._bytes,
                    'crc_discarded': self._stream.discarded,
                    'pending_bytes': len(self._stream.buffer),
                    'layout_rejected': self._rejected,
                    'encrypted_frames_ignored': self._encrypted,
                    'packet_rate_hz': len(self._frame_times),
                    'read_only': True, 'application_bytes_sent': 0,
                    'last_error': self._error, 'source_detail': self._source_detail,
                },
                'aircraft': channel(self._aircraft), 'gimbal': channel(self._gimbal),
                'physical_calibration_verified': False,
                'clock_basis': 'PC monotonic receipt time; sensor clock unverified',
            }
