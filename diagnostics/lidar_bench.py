#!/usr/bin/env python3
"""Local target annotations beside an existing Wi-Fi recorder; no device API."""
import argparse
import datetime as dt
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
import time
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

STEPS = (
    ('Clear baseline', None), ('Centered target', 1.0),
    ('Centered target', .5), ('Centered target', 2.0),
    ('Centered target', 1.0), ('Centered target', 2.0),
    ('Centered target', .5), ('Centered target', 1.0),
    ('Clear return baseline', None),
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class TokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta' and attrs.get('name') == 'neo2-token':
            self.tokens.append(attrs.get('content', ''))


class CameraReader:
    """GET-only reader of one fixed loopback server; never an aircraft client."""
    def __init__(self, capture_root, port=8793):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('invalid_camera_port')
        self.root = Path(capture_root).resolve(strict=True)
        self.base = f'http://127.0.0.1:{port}'
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.token = None

    def get(self, path, limit=262144):
        headers = {'X-Neo2-Token': self.token} if self.token else {}
        with self.opener.open(Request(self.base + path, headers=headers, method='GET'), timeout=2) as r:
            body = r.read(limit + 1)
        if len(body) > limit:
            raise ValueError('local_response_too_large')
        return body

    def sample(self):
        if self.token is None:
            parser = TokenParser()
            parser.feed(self.get('/').decode('utf-8'))
            if len(parser.tokens) != 1 or not re.fullmatch('[a-f0-9]{64}', parser.tokens[0]):
                raise ValueError('local_camera_token_unavailable')
            self.token = parser.tokens[0]
        s = json.loads(self.get('/api/camera/status', 65536))
        if (s.get('preview_only') is not True or s.get('flight_commands_available') is not False
                or s.get('source_mode') != 'live_aircraft'):
            raise ValueError('preview_only_receiver_required')
        generation = s.get('session_generation')
        if not isinstance(generation, str) or not re.fullmatch('[a-f0-9]{24}', generation):
            raise ValueError('waiting_for_camera_session')
        if s.get('state') not in ('connecting', 'connected'):
            raise ValueError('waiting_for_live_wifi_capture')
        directory = self.root / generation
        path = directory / 'swudp.jsonl'
        if directory.is_symlink() or directory.resolve() != directory or path.is_symlink():
            raise ValueError('capture_symlink_rejected')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or not 0 <= time.time() - info.st_mtime <= 3:
                raise ValueError('capture_file_not_fresh')
            start = max(0, info.st_size - 131072)
            source.seek(start)
            tail = source.read(131072).splitlines()
        if start and tail:
            tail = tail[1:]
        received = []
        for line in tail:
            try:
                row = json.loads(line)
                stamp = row.get('monotonic_ns')
                if (row.get('interface') == 'udp' and row.get('direction') == 'rx'
                        and type(stamp) is int and row.get('raw_hex')):
                    received.append(stamp)
            except (ValueError, AttributeError):
                continue
        now = time.monotonic_ns()
        latest_rx = max(received, default=0)
        if not latest_rx or not 0 <= now - latest_rx <= 3_000_000_000:
            raise ValueError('fresh_receive_packet_required')
        return {'generation': generation, 'capture_path': str(path),
                'device': info.st_dev, 'inode': info.st_ino, 'bytes': info.st_size,
                'frames_encoded': s.get('video', {}).get('frames_encoded', 0),
                'rx_monotonic_ns': latest_rx,
                'camera_image_live': s.get('video', {}).get('live') is True,
                'owner_state': s.get('state'), 'owner_connected': s.get('connected')}


class Bench:
    def __init__(self, reader, output, *, settle=3., hold=5., interval=.5):
        self.reader, self.output = reader, Path(output)
        self.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.events = self.output / 'target-windows.private.json'
        self.settle, self.hold, self.interval = settle, hold, interval
        self.lock = threading.RLock()
        self.rows, self.active, self.generation, self.index = [], None, None, 0
        self.error, self.last_ready = None, False
        self.token = secrets.token_hex(32)
        self._save()

    def _save(self):
        value = {'schema': 'neo2.target-windows.v1', 'mode': 'operator_physical_annotations',
                 'clock': 'same-Mac time.monotonic_ns; receipt time, not sensor time',
                 'distance_reference': 'front edge of airframe to near face of board',
                 'sensor_origin_offset_verified': False, 'range_decoder_verified': False,
                 'annotation_process_device_commands': 0, 'session_generation': self.generation,
                 'steps': [{'label': label, 'expected_distance_m': distance} for label, distance in STEPS],
                 'windows': self.rows}
        temporary = self.output / ('write-' + secrets.token_hex(4) + '.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream, indent=2, allow_nan=False)
                stream.write('\n')
            temporary.replace(self.events)
        finally:
            temporary.unlink(missing_ok=True)

    def snapshot(self):
        try:
            sample = self.reader.sample()
            ready = self.generation in (None, sample['generation'])
            message = ('Wi-Fi capture is live' if sample.get('camera_image_live') else
                       'Wi-Fi capture is live · no camera image required') if ready else 'Session changed; start a new test'
        except Exception as error:
            reasons = {'waiting_for_camera_session': 'Waiting for an approved camera session',
                       'waiting_for_live_wifi_capture': 'Waiting for the Wi-Fi session owner',
                       'fresh_receive_packet_required': 'Waiting for fresh received Wi-Fi packets',
                       'capture_file_not_fresh': 'Waiting for the capture file to update',
                       'preview_only_receiver_required': 'Existing receiver is not in preview-only mode'}
            ready, message = False, reasons.get(str(error), 'Waiting for the existing camera capture')
        with self.lock:
            self.last_ready = ready
            active = dict(self.active) if self.active else None
            if active:
                now = time.monotonic_ns()
                active = {'phase': 'Settle' if now < active['start_monotonic_ns'] else 'Hold still',
                          'remaining_seconds': max(0, (active['end_monotonic_ns'] - now) / 1e9)}
            return {'ready': ready, 'message': message, 'index': self.index, 'total': len(STEPS),
                    'steps': [{'label': a, 'distance_m': b} for a, b in STEPS],
                    'active': active, 'completed': self.index == len(STEPS), 'error': self.error,
                    'recorded_windows': len(self.rows), 'token': self.token,
                    'valid_windows': sum(r['valid'] for r in self.rows)}

    def start(self, data):
        if not isinstance(data, dict) or set(data) != {'measured', 'width_cm', 'height_cm'}:
            raise ValueError('Confirm the measurement and target dimensions')
        if data['measured'] is not True:
            raise ValueError('Measure the target position before recording')
        for k in ('width_cm', 'height_cm'):
            if type(data[k]) not in (int, float) or not 10 <= data[k] <= 300:
                raise ValueError('Enter target dimensions between 10 and 300 cm')
        sample = self.reader.sample()
        with self.lock:
            if self.active is not None or self.index >= len(STEPS) or len(self.rows) >= 40:
                raise ValueError('A hold is running, the test is complete, or the retry limit was reached')
            if self.generation not in (None, sample['generation']):
                raise ValueError('Session changed; start a new test')
            self.generation = sample['generation']
            now = time.monotonic_ns()
            self.active = {'step_index': self.index, 'label': STEPS[self.index][0],
                           'expected_distance_m': STEPS[self.index][1],
                           'start_monotonic_ns': now + int(self.settle * 1e9),
                           'end_monotonic_ns': now + int((self.settle + self.hold) * 1e9),
                           'operator_reference': 'tape_measured' if STEPS[self.index][1] is not None else 'clear_scene',
                           'target_width_cm': data['width_cm'], 'target_height_cm': data['height_cm'],
                           'capture': sample, 'requested_at_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
            self.error = None
            threading.Thread(target=self._record, daemon=True).start()

    def _record(self):
        with self.lock:
            record = dict(self.active)
        reason, last_sample, previous = None, record['capture'], time.monotonic_ns()
        try:
            while time.monotonic_ns() < record['end_monotonic_ns']:
                time.sleep(self.interval)
                sample = self.reader.sample()
                current = time.monotonic_ns()
                if current - previous > 2_500_000_000:
                    raise ValueError('local_observation_gap')
                previous = current
                if any(sample[k] != record['capture'][k] for k in ('generation', 'device', 'inode')):
                    raise ValueError('capture_session_changed')
                if sample['bytes'] < last_sample['bytes']:
                    raise ValueError('capture_truncated')
                last_sample = sample
            if last_sample['bytes'] <= record['capture']['bytes']:
                raise ValueError('capture_did_not_grow')
            if last_sample['rx_monotonic_ns'] <= record['capture']['rx_monotonic_ns']:
                raise ValueError('receive_capture_did_not_advance')
        except Exception:
            reason = 'Capture was interrupted; repeat this position after reconnecting'
        record.update(valid=reason is None, failure=reason, finished_monotonic_ns=time.monotonic_ns(),
                      capture_bytes_at_finish=last_sample['bytes'])
        with self.lock:
            self.rows.append(record)
            if reason is None:
                self.index += 1
            self.error = reason
            try:
                self._save()
            except Exception:
                self.error = 'Local save failed; stop the test'
                if reason is None:
                    self.index -= 1
            self.active = None


def handler(bench):
    assets = Path(__file__).resolve().parents[1] / 'viewer'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, value, kind='application/json'):
            body = value if isinstance(value, bytes) else json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            for k, v in {'Content-Type': kind, 'Content-Length': str(len(body)), 'Cache-Control': 'no-store',
                         'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
                         'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"}.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def local(self):
            hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            return (self.headers.get('Host') in hosts and
                    self.headers.get('Origin') in (None, *(f'http://{h}' for h in hosts)))

        def do_GET(self):
            if not self.local():
                return self.reply(403, {'error': 'Local page only'})
            if self.path == '/api/state':
                return self.reply(200, bench.snapshot())
            names = {'/': ('lidar-bench.html', 'text/html'), '/lidar-bench.js': ('lidar-bench.js', 'text/javascript'),
                     '/lidar-bench.css': ('lidar-bench.css', 'text/css')}
            if self.path not in names:
                return self.reply(404, {'error': 'Not found'})
            name, kind = names[self.path]
            self.reply(200, (assets / name).read_bytes(), kind + '; charset=utf-8')

        def do_POST(self):
            if not self.local():
                return self.reply(403, {'error': 'Local page only'})
            if not hmac.compare_digest(self.headers.get('X-Bench-Token', ''), bench.token):
                return self.reply(403, {'error': 'Reload the local page'})
            if self.path != '/api/hold':
                return self.reply(404, {'error': 'Not found'})
            try:
                self.connection.settimeout(3)
                size = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Content-Type') != 'application/json' or not 0 < size <= 1024:
                    raise ValueError('Invalid annotation')
                bench.start(json.loads(self.rfile.read(size)))
            except (ValueError, OSError) as error:
                return self.reply(409, {'error': str(error) if isinstance(error, ValueError) else 'Camera capture is unavailable'})
            self.reply(202, {'accepted': True})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New private annotation directory')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--camera-port', type=int, default=8793)
    args = parser.parse_args()
    bench = Bench(CameraReader(args.capture_root, args.camera_port), args.output)
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler(bench)) as server:
        server.daemon_threads = True
        print(f'Target annotations: http://127.0.0.1:{server.server_port}/ (local saves only)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
