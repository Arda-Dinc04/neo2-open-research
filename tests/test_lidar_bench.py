"""Synthetic timing/identity checks; no aircraft, BLE or Wi-Fi session."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from urllib.error import HTTPError

SPEC = importlib.util.spec_from_file_location('lidar_bench', Path(__file__).resolve().parents[1] / 'diagnostics/lidar_bench.py')
bench_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench_module)


class Reader:
    def __init__(self):
        self.count = 0
        self.changed = False
        self.frozen = False
        self.failed = False

    def sample(self):
        if self.failed:
            raise ValueError('not_live')
        self.count += not self.frozen
        return {'generation': 'b' * 24 if self.changed else 'a' * 24,
                'device': 1, 'inode': 2, 'capture_path': '/synthetic/swudp.jsonl',
                'bytes': self.count, 'frames_encoded': self.count,
                'rx_monotonic_ns': self.count, 'camera_image_live': False}


class LidarBenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reader = Reader()
        self.bench = bench_module.Bench(self.reader, Path(self.temp.name) / 'private',
                                       settle=.02, hold=.03, interval=.01)

    def wait(self):
        deadline = time.monotonic() + 2
        while self.bench.active is not None and time.monotonic() < deadline:
            time.sleep(.005)
        self.assertIsNone(self.bench.active)

    def start(self):
        self.bench.start({'measured': True, 'width_cm': 60, 'height_cm': 80})

    def test_hold_retains_receipt_window_reference_and_private_permissions(self):
        self.start()
        self.wait()
        record = json.loads(self.bench.events.read_text())
        self.assertTrue(record['windows'][0]['valid'])
        self.assertIsNone(record['windows'][0]['expected_distance_m'])
        self.assertGreater(record['windows'][0]['end_monotonic_ns'], record['windows'][0]['start_monotonic_ns'])
        self.assertFalse(record['sensor_origin_offset_verified'])
        self.assertFalse(record['range_decoder_verified'])
        self.assertEqual(record['annotation_process_device_commands'], 0)
        self.assertEqual(os.stat(self.bench.events).st_mode & 0o777, 0o600)
        self.assertEqual(self.bench.index, 1)

    def test_connection_loss_cannot_advance_position(self):
        self.start()
        self.reader.failed = True
        self.wait()
        self.assertFalse(self.bench.rows[0]['valid'])
        self.assertEqual(self.bench.index, 0)

    def test_generation_change_cannot_mix_a_window_or_resume_test(self):
        self.start()
        self.reader.changed = True
        self.wait()
        self.assertFalse(self.bench.rows[0]['valid'])
        self.assertEqual(self.bench.index, 0)
        with self.assertRaisesRegex(ValueError, 'Session changed'):
            self.start()

    def test_stopped_capture_cannot_be_validated_by_live_label(self):
        self.reader.frozen = True
        self.start()
        self.wait()
        self.assertFalse(self.bench.rows[0]['valid'])

    def test_duplicate_click_and_unmeasured_or_invalid_dimensions_rejected(self):
        for data in ({'measured':False,'width_cm':60,'height_cm':60},
                     {'measured':True,'width_cm':float('nan'),'height_cm':60},
                     {'measured':True,'width_cm':60,'height_cm':60,'command':'send'}):
            with self.assertRaises(ValueError):
                self.bench.start(data)
        self.start()
        with self.assertRaises(ValueError):
            self.start()
        self.wait()

    def test_unavailable_receiver_remains_waiting(self):
        self.reader.failed = True
        state = self.bench.snapshot()
        self.assertFalse(state['ready'])
        self.assertEqual(state['valid_windows'], 0)

    def camera_reader(self, *, direction='rx', age=0, state='connected', connected=True):
        root = Path(self.temp.name)
        folder = root / ('a' * 24)
        folder.mkdir()
        path = folder / 'swudp.jsonl'
        path.write_text(json.dumps({'interface': 'udp', 'direction': direction,
            'monotonic_ns': time.monotonic_ns() - int(age * 1e9), 'raw_hex': '0011'}) + '\n')
        reader = bench_module.CameraReader(root)
        reader.token = 'c' * 64
        status = {'source_mode': 'live_aircraft', 'preview_only': True,
                  'flight_commands_available': False, 'session_generation': 'a' * 24,
                  'state': state, 'connected': connected, 'video': {'live': False, 'frames_encoded': 0}}
        reader.get = lambda *args: json.dumps(status).encode()
        return reader

    def test_fresh_receive_packets_allow_bench_without_camera_frames(self):
        result = self.camera_reader().sample()
        self.assertFalse(result['camera_image_live'])
        self.assertGreater(result['rx_monotonic_ns'], 0)

    def test_fresh_receive_during_camera_preparation_does_not_require_application_ready(self):
        result = self.camera_reader(state='connecting', connected=False).sample()
        self.assertGreater(result['rx_monotonic_ns'], 0)

    def test_stopped_owner_cannot_reuse_recent_capture_tail(self):
        with self.assertRaisesRegex(ValueError, 'live_wifi_capture'):
            self.camera_reader(state='failed', connected=False).sample()

    def test_fresh_tx_file_cannot_pass_as_receive_capture(self):
        with self.assertRaisesRegex(ValueError, 'receive'):
            self.camera_reader(direction='tx').sample()

    def test_old_rx_timestamp_cannot_pass_on_new_file_mtime(self):
        with self.assertRaisesRegex(ValueError, 'receive'):
            self.camera_reader(age=10).sample()

    def test_restarted_camera_owner_expires_cached_token_without_sending_a_post(self):
        reader = bench_module.CameraReader(Path(self.temp.name))
        reader.token = 'c' * 64
        class Unauthorized:
            def open(self, request, **kwargs):
                self.request = request
                raise HTTPError(request.full_url, 401, 'Unauthorized', {}, None)
        opener = Unauthorized()
        reader.opener = opener
        with self.assertRaisesRegex(ValueError, 'token_expired'):
            reader.get('/api/camera/status')
        self.assertIsNone(reader.token)
        self.assertEqual(opener.request.get_method(), 'GET')

    def test_non_auth_http_error_does_not_discard_owner_token(self):
        reader = bench_module.CameraReader(Path(self.temp.name))
        reader.token = 'c' * 64
        class Missing:
            def open(self, request, **kwargs):
                raise HTTPError(request.full_url, 404, 'Not found', {}, None)
        reader.opener = Missing()
        with self.assertRaises(HTTPError) as caught:
            reader.get('/api/camera/status')
        caught.exception.close()
        self.assertEqual(reader.token, 'c' * 64)


if __name__ == '__main__':
    unittest.main()
