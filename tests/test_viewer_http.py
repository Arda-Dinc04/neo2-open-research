import http.client
import json
from pathlib import Path
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from viewer_server import ViewerApplication, ViewerServer


class SampleState:
    def snapshot(self):
        sample = {'angles_deg': [0, 1, 2], 'raw': [0, 10, 20], 'age_ms': 0, 'source': {}}
        return {'mode': 'live', 'status': 'streaming', 'aircraft': sample, 'gimbal': dict(sample)}

    def history_snapshot(self, since=None):
        now = time.monotonic()
        return [{'timestamp': now - lag, 'kind': kind, 'angles_deg': [0, 1, 2]}
                for kind in ('aircraft', 'gimbal') for lag in (1.6, 0.8, 0.1)]


class ViewerHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = ViewerApplication(SampleState(), Path(__file__).resolve().parents[1] / 'viewer')
        cls.server = ViewerServer(0, cls.app)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            data = response.read()
            return response.status, dict(response.getheaders()), data
        finally:
            connection.close()

    def annotations(self):
        return {'Origin': f'http://127.0.0.1:{self.port}',
                'X-Viewer-Token': self.app.token, 'Content-Type': 'application/json'}

    def test_state_is_readonly_and_no_cross_origin_header_is_enabled(self):
        status, headers, raw = self.request('GET', '/api/state')
        self.assertEqual(status, 200)
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertFalse(json.loads(raw)['calibration']['physical_axes_verified'])

    def test_foreign_host_cannot_read_state(self):
        self.assertEqual(self.request('GET', '/api/state', headers={'Host': 'untrusted.example'})[0], 403)

    def test_annotations_require_same_origin_and_token(self):
        body = json.dumps({'label': 'baseline'})
        self.assertEqual(self.request('POST', '/api/bench/marker', body)[0], 403)
        headers = self.annotations()
        headers['Origin'] = 'https://untrusted.example'
        self.assertEqual(self.request('POST', '/api/bench/marker', body, headers)[0], 403)
        headers = self.annotations()
        headers['X-Viewer-Token'] = 'invalid'
        self.assertEqual(self.request('POST', '/api/bench/marker', body, headers)[0], 403)
        headers['X-Viewer-Token'] = 'é'
        self.assertEqual(self.request('POST', '/api/bench/marker', body, headers)[0], 403)

    def test_only_annotations_are_routed_and_validated(self):
        body = json.dumps({'label': 'x', 'command': 'anything'})
        self.assertEqual(self.request('POST', '/api/bench/marker', body, self.annotations())[0], 409)
        self.assertEqual(self.request('POST', '/api/unknown-command', '{}', self.annotations())[0], 404)
        self.assertEqual(self.request('GET', '/../LICENSE')[0], 404)

    def test_annotation_and_export_never_claim_calibration(self):
        status, _, raw = self.request('POST', '/api/bench/marker', json.dumps({'label': 'http test baseline'}), self.annotations())
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)['marker']['verified'])
        status, headers, raw = self.request('GET', '/api/bench/export.json')
        self.assertEqual(status, 200)
        self.assertIn('attachment', headers['Content-Disposition'])
        self.assertEqual(json.loads(raw)['drone_commands_sent_by_viewer'], 0)

    def test_oversize_annotation_is_rejected_before_body_read(self):
        headers = self.annotations()
        headers['Content-Length'] = '9000'
        self.assertEqual(self.request('POST', '/api/bench/marker', '{}', headers)[0], 409)


if __name__ == '__main__':
    unittest.main()
