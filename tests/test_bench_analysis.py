from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.bench_analysis import analyze_session, delta


def session():
    inputs = [('Stationary baseline', 'baseline', [0, 0, 0], None),
              ('yaw', 'yaw', [0, 0, 90], 90),
              ('yaw return', 'baseline', [0, 0, 0], None),
              ('pitch', 'pitch', [15, 0, 0], 15),
              ('pitch return', 'baseline', [0, 0, 0], None),
              ('roll', 'roll', [0, 15, 0], 15),
              ('finish', 'end', [0, 0, 0], None)]
    return {'session_id': 'synthetic', 'markers': [
        {'label': name, 'expected_axis': axis, 'expected_degrees': degrees,
         'mode': 'live', 'aircraft': angles, 'gimbal': [0, 0, angles[2]],
         'aircraft_delta': [999, 999, 999], 'aircraft_sample': {'sample_count': 4},
         'gimbal_sample': {'sample_count': 10}}
        for name, axis, angles, degrees in inputs]}


class BenchAnalysisTests(unittest.TestCase):
    def test_axis_mapping_is_derived_from_absolute_samples(self):
        result = analyze_session(session(), 'estimated')
        self.assertTrue(result['complete_first_cycle'])
        self.assertEqual({key: value['physical_axis'] for key, value in
                          result['candidate_axis_mapping'].items()}, {'A': 'pitch', 'B': 'roll', 'C': 'yaw'})
        self.assertEqual(result['movements'][0]['dominant_delta_deg'], 90)
        self.assertFalse(result['physical_calibration_verified'])

    def test_measured_reference_alone_does_not_claim_repeated_accuracy(self):
        result = analyze_session(session(), 'measured')
        self.assertFalse(any(row['scale_validated'] for row in result['movements']))
        self.assertFalse(result['repeatability_established'])

    def test_negative_direction_preserves_positive_axis_convention(self):
        data = session()
        data['markers'][1]['aircraft'][2] = -90
        data['markers'][1]['expected_degrees'] = -90
        row = analyze_session(data)['movements'][0]
        self.assertEqual(row['sign_for_positive_operator_action'], 'positive')

    def test_wrap_and_latest_duplicate_baseline(self):
        self.assertEqual(delta([-179, 0, 0], [179, 0, 0]), [2, 0, 0])
        data = session()
        data['markers'].insert(0, dict(data['markers'][0]))
        result = analyze_session(data)
        self.assertEqual(result['duplicate_or_earlier_baselines'], 1)
        self.assertTrue(result['complete_first_cycle'])

    def test_replayed_and_nonfinite_input_is_rejected(self):
        data = session()
        data['markers'][1]['mode'] = 'replay'
        with self.assertRaises(ValueError):
            analyze_session(data)
        data = session()
        data['markers'][1]['aircraft'][0] = float('nan')
        with self.assertRaises(ValueError):
            analyze_session(data)


if __name__ == '__main__':
    unittest.main()
