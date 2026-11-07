"""Loopback-only viewer and local bench annotations; no drone-command API."""
import datetime as dt
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import secrets
import statistics
import threading
import time
from urllib.parse import urlsplit

from transport.bench_evidence import finite_vector, gimbal_pair_evidence, route_key


def wrap_angle(value):
    return (value + 180) % 360 - 180


def angle_delta(current, baseline):
    return [round(wrap_angle(a - b), 4) for a, b in zip(current, baseline)]


class BenchRecorder:
    """Records operator observations, never marks a physical axis calibrated."""
    def __init__(self, state, destination=None):
        self.state = state
        self.destination = Path(destination) if destination else None
        self.session_id = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + secrets.token_hex(3)
        self.markers = []
        self.baseline = None
        self.lock = threading.RLock()

    def snapshot(self):
        with self.lock:
            return {'session_id': self.session_id,
                    'stage': self.markers[-1]['label'] if self.markers else 'idle',
                    'markers': [self._summary(marker) for marker in self.markers], 'physical_axes_verified': False}

    @staticmethod
    def _summary(marker):
        # Polling and annotation responses carry counts, not bulk evidence.
        result = dict(marker)
        sample = dict(result['gimbal_sample'])
        if 'paired_evidence' in sample:
            sample['paired_evidence'] = {key: value for key, value in sample['paired_evidence'].items() if key != 'samples'}
        result['gimbal_sample'] = sample
        return copy.deepcopy(result)

    def _recent_sample(self, snapshot, kind, now):
        value = snapshot.get(kind)
        if (not value or type(value.get('age_ms')) not in (int, float)
                or not math.isfinite(value['age_ms']) or not 0 <= value['age_ms'] <= 500):
            raise ValueError('Both aircraft and gimbal readings must be fresh before recording a marker')
        angles = value.get('angles_deg')
        if not finite_vector(angles, 3):
            raise ValueError('No valid angle sample available')
        try:
            history = self.state.history_snapshot(since=now - 2.0)
        except (AttributeError, TypeError):
            history = []
        anchor = route_key(value.get('source'))
        observer = value.get('observer_session_id')
        recent = [h for h in history if h.get('kind') == kind
                   and type(h.get('timestamp')) in (int, float) and math.isfinite(h['timestamp'])
                   and now - 2.0 <= h['timestamp'] <= now and finite_vector(h.get('angles_deg'), 3)
                   and (anchor is None or route_key(h.get('source')) == anchor)
                   and (observer is None or h.get('observer_session_id') == observer)]
        samples = [h['angles_deg'] for h in recent]
        span = max((h['timestamp'] for h in recent), default=now) - min((h['timestamp'] for h in recent), default=now)
        if len(samples) < 3 or span < 1.0:
            raise ValueError(f'Hold this pose steady for at least 3 seconds; {kind} needs 3 samples spanning at least 1 second')
        # Center circular samples around the current reading before averaging
        # so +179/-179 does not become a false zero-degree median.
        columns = [[a + wrap_angle(v[i] - a) for v in samples] for i, a in enumerate(angles)]
        median = [wrap_angle(statistics.median(col)) for col in columns]
        spread = [round(max(col) - min(col), 4) for col in columns]
        result = {'angles': [round(a, 4) for a in median], 'sample_count': len(samples),
                'spread_deg': spread, 'source': value.get('source'), 'age_ms': value['age_ms'],
                'sampling_window_s': 2.0, 'observed_span_s': round(span, 3),
                'stable_within_2_deg': max(spread) <= 2.0}
        if kind == 'gimbal':
            result['paired_evidence'] = gimbal_pair_evidence(recent, value.get('source'), observer, now)
        return result

    def add(self, data):
        if not isinstance(data, dict) or set(data) - {'label', 'expected_axis', 'expected_degrees'}:
            raise ValueError('Only label, expected_axis and expected_degrees annotations are accepted')
        label = data.get('label')
        axis = data.get('expected_axis', 'baseline')
        degrees = data.get('expected_degrees')
        if not isinstance(label, str) or not label.strip() or len(label) > 96:
            raise ValueError('A marker label of 1–96 characters is required')
        if axis not in ('baseline', 'yaw', 'pitch', 'roll', 'end'):
            raise ValueError('Unrecognized bench observation axis')
        if degrees is not None and (type(degrees) not in (int, float)
                                   or not math.isfinite(degrees) or abs(degrees) > 360):
            raise ValueError('Expected angle must be a finite number between -360 and 360')
        snap = self.state.snapshot()
        if snap.get('mode') != 'live' or snap.get('status') != 'streaming':
            raise ValueError('Bench validation requires fresh live USB data; replay/demo cannot validate axes')
        now = time.monotonic()
        aircraft = self._recent_sample(snap, 'aircraft', now)
        gimbal = self._recent_sample(snap, 'gimbal', now)
        with self.lock:
            if len(self.markers) >= 200:
                raise ValueError('Bench session marker limit reached')
            marker = {'label': label.strip(), 'expected_axis': axis, 'expected_degrees': degrees,
                      'created_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                      'aircraft': aircraft['angles'], 'gimbal': gimbal['angles'],
                      'aircraft_sample': aircraft, 'gimbal_sample': gimbal,
                      'verified': False, 'mode': 'live'}
            previous_baseline = self.baseline
            if axis == 'baseline':
                self.baseline = marker
            marker['aircraft_delta'] = angle_delta(marker['aircraft'], self.baseline['aircraft']) if self.baseline else None
            marker['gimbal_delta'] = angle_delta(marker['gimbal'], self.baseline['gimbal']) if self.baseline else None
            marker['baseline_label'] = self.baseline['label'] if self.baseline else None
            self.markers.append(marker)
            try:
                self._save()
            except (OSError, ValueError, TypeError):
                self.markers.pop()
                self.baseline = previous_baseline
                raise
            return self._summary(marker)

    def export(self):
        with self.lock:
            result = self.snapshot()
            result['markers'] = copy.deepcopy(self.markers)
        return {'format': 'neo2-open-research/bench/v1', **result,
                'interpretation': 'Operator annotations and source-backed fields; no automatic physical calibration',
                'sensor_clock_verified': False, 'drone_commands_sent_by_viewer': 0}

    def _save(self):
        if not self.destination:
            return
        self.destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.destination / (self.session_id + '.json')
        body = json.dumps(self.export(), indent=2, allow_nan=False) + '\n'
        temp = path.with_suffix('.' + secrets.token_hex(4) + '.tmp')
        fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as output:
                output.write(body)
            temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)


class ViewerApplication:
    def __init__(self, state, viewer_directory, session_directory=None):
        self.state = state
        self.viewer_directory = Path(viewer_directory).resolve()
        self.bench = BenchRecorder(state, session_directory)
        self.token = secrets.token_urlsafe(32)

    def snapshot(self):
        result = self.state.snapshot()
        result.update({'schema_version': 1, 'bench': self.bench.snapshot(),
                       'api_token': self.token,
                       'calibration': {'physical_axes_verified': False, 'display_zero_changes_hardware': False},
                       'video': {'status': 'not_connected', 'owner': 'Neo 2 video viewer chat'}})
        return result


class ViewerServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port, application):
        self.application = application
        super().__init__(('127.0.0.1', port), ViewerHandler)


class ViewerHandler(BaseHTTPRequestHandler):
    server_version = 'Neo2ReadOnlyViewer/1'

    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format, *args):
        # Polling emits no access log; errors remain visible in API state.
        pass

    def _allowed_host(self):
        port = self.server.server_address[1]
        return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

    def _reply(self, status, body, content_type='application/json', download=False):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'")
        if download:
            self.send_header('Content-Disposition', 'attachment; filename="neo2-bench-session.json"')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if not self._allowed_host():
            self._reply(403, {'error': 'Loopback host only'})
            return
        path = urlsplit(self.path).path
        if path == '/api/state':
            self._reply(200, self.server.application.snapshot())
        elif path == '/api/routes':
            census = self.server.application.state.snapshot().get('route_census')
            if census is None:
                self._reply(503, {'error': 'Route census unavailable from this source'})
            else:
                self._reply(200, census)
        elif path == '/api/bench/export.json':
            self._reply(200, self.server.application.bench.export(), download=True)
        elif path == '/healthz':
            self._reply(200, {'ok': True, 'read_only': True})
        elif path in ('/', '/index.html', '/app.js', '/styles.css'):
            name = 'index.html' if path == '/' else path[1:]
            content_types = {'index.html': 'text/html; charset=utf-8',
                             'app.js': 'text/javascript; charset=utf-8',
                             'styles.css': 'text/css; charset=utf-8'}
            try:
                content = (self.server.application.viewer_directory / name).read_bytes()
            except FileNotFoundError:
                self._reply(404, {'error': 'Viewer asset not found'})
                return
            self._reply(200, content, content_types[name])
        else:
            self._reply(404, {'error': 'Unknown read-only viewer route'})

    def do_POST(self):
        port = self.server.server_address[1]
        origins = (f'http://127.0.0.1:{port}', f'http://localhost:{port}')
        if not self._allowed_host() or self.headers.get('Origin') not in origins:
            self._reply(403, {'error': 'Same-origin annotation required'})
            return
        token = self.headers.get('X-Viewer-Token', '')
        if not token.isascii() or len(token) != len(self.server.application.token) or not secrets.compare_digest(token, self.server.application.token):
            self._reply(403, {'error': 'Invalid viewer annotation token'})
            return
        if urlsplit(self.path).path != '/api/bench/marker':
            self._reply(404, {'error': 'No drone command routes exist'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
            self._reply(415, {'error': 'JSON annotations only'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2048:
                raise ValueError('Annotation request exceeds limit or has no body')
            data = json.loads(self.rfile.read(length))
            marker = self.server.application.bench.add(data)
        except (ValueError, UnicodeDecodeError) as exc:
            self._reply(409, {'error': str(exc)})
            return
        except TimeoutError:
            self._reply(408, {'error': 'Annotation body timed out'})
            return
        except OSError:
            self._reply(500, {'error': 'Could not persist the local bench annotation'})
            return
        self._reply(200, {'ok': True, 'marker': marker, 'bench': self.server.application.bench.snapshot()})
