import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from viewer_server import BenchRecorder, ViewerApplication, angle_delta


class FakeState:
    def __init__(self, mode='live', status='streaming'):
        self.mode, self.status = mode, status
        self.angles = [179, 0, 0]
        self.age = 20

    def snapshot(self):
        channel = {'angles_deg': list(self.angles), 'raw': [1790, 0, 0],
                   'age_ms': self.age, 'source': {'command': '03/43'}}
        return {'mode': self.mode, 'status': self.status,
                'aircraft': dict(channel), 'gimbal': dict(channel)}

    def history_snapshot(self, since=None):
        now = time.monotonic()
        return [{'timestamp': now - lag, 'kind': kind, 'angles_deg': list(self.angles)}
                for kind in ('aircraft', 'gimbal') for lag in (1.6, 0.8, 0.1)]


class ViewerServerTests(unittest.TestCase):
    def test_wrap_around_does_not_create_full_rotation(self):
        self.assertEqual(angle_delta([-179, 1, 2], [179, 0, 0]), [2, 1, 2])

    def test_replay_demo_stale_and_missing_samples_cannot_validate(self):
        for mode, status in [('replay', 'streaming'), ('demo', 'streaming'), ('live', 'stale')]:
            with self.assertRaises(ValueError):
                BenchRecorder(FakeState(mode, status)).add({'label': 'baseline'})
        state = FakeState()
        state.age = 501
        with self.assertRaises(ValueError):
            BenchRecorder(state).add({'label': 'baseline'})

    def test_local_annotations_persist_without_changing_source_angles(self):
        state = FakeState()
        with tempfile.TemporaryDirectory() as tmp:
            recorder = BenchRecorder(state, tmp)
            recorder.add({'label': 'baseline', 'expected_axis': 'baseline'})
            state.angles = [-179, 10, 0]
            marker = recorder.add({'label': 'yaw +90', 'expected_axis': 'yaw', 'expected_degrees': 90})
            self.assertEqual(marker['aircraft_delta'], [2, 10, 0])
            self.assertFalse(marker['verified'])
            self.assertEqual(state.angles, [-179, 10, 0])
            saved = json.loads(next(Path(tmp).glob('*.json')).read_text())
            self.assertEqual(len(saved['markers']), 2)
            self.assertEqual(saved['drone_commands_sent_by_viewer'], 0)

    def test_arbitrary_command_keys_and_invalid_angles_are_rejected(self):
        recorder = BenchRecorder(FakeState())
        for payload in ({'label': 'x', 'command': 'takeoff'},
                        {'label': 'x', 'expected_degrees': float('nan')},
                        {'label': 'x', 'expected_axis': 'motor'},
                        {'label': 'x', 'expected_degrees': True}):
            with self.assertRaises(ValueError):
                recorder.add(payload)

    def test_state_announces_video_boundary_and_unverified_axes(self):
        app = ViewerApplication(FakeState(), Path('.'))
        state = app.snapshot()
        self.assertEqual(state['video']['status'], 'not_connected')
        self.assertFalse(state['calibration']['physical_axes_verified'])
        self.assertGreaterEqual(len(state['api_token']), 32)

    def test_median_is_circular_across_yaw_boundary(self):
        state = FakeState()
        state.history_snapshot = lambda since=None: [
            {'timestamp': time.monotonic() - lag, 'kind': kind, 'angles_deg': [value, 0, 0]}
            for kind in ('aircraft', 'gimbal') for lag, value in ((1.6, -179), (0.8, 179), (0.1, -180))]
        marker = BenchRecorder(state).add({'label': 'baseline'})
        self.assertEqual(abs(marker['aircraft'][0]), 180)
        self.assertEqual(marker['aircraft_sample']['spread_deg'][0], 2)

    def test_failed_persistence_does_not_leave_a_phantom_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'not-a-directory'
            path.write_text('test')
            recorder = BenchRecorder(FakeState(), path)
            with self.assertRaises(OSError):
                recorder.add({'label': 'baseline'})
            self.assertEqual(recorder.markers, [])
            self.assertIsNone(recorder.baseline)

    def test_single_snapshot_or_burst_cannot_establish_stability(self):
        state = FakeState()
        state.history_snapshot = lambda since=None: []
        with self.assertRaisesRegex(ValueError, '3 samples'):
            BenchRecorder(state).add({'label': 'baseline'})
        state.history_snapshot = lambda since=None: [
            {'timestamp': time.monotonic(), 'kind': kind, 'angles_deg': list(state.angles)}
            for kind in ('aircraft', 'gimbal') for _ in range(3)]
        with self.assertRaisesRegex(ValueError, '1 second'):
            BenchRecorder(state).add({'label': 'baseline'})


if __name__ == '__main__':
    unittest.main()
