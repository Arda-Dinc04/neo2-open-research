"""Synthetic packets test private evidence retention, never physical calibration."""
import copy
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.bench_analysis import analyze_session, read_bench_session
from transport.bench_evidence import gimbal_pair_evidence, summarize_exported_gimbal_pairs
from transport.live_source import _synthetic_packet
from transport.live_state import LiveState
from transport.duml_observer import crc16
from viewer_server import BenchRecorder


def synthetic_pose(sequence, receiver=0x2a, quaternion=None):
    payload = bytearray(50)
    struct.pack_into('<hhh', payload, 0, sequence, -10, 20)
    payload[6:16] = b'PRIVATE-ID'
    # Deliberately preserve equivalent opposite signs and negative zero.
    q = quaternion or ((1.0, -0.0, 0.0, 0.0) if sequence % 2 else (-1.0, 0.0, 0.0, 0.0))
    struct.pack_into('<ffff', payload, 24, *q)
    return _synthetic_packet(4, receiver, (4, 5), sequence, payload)


def synthetic_state(count=3, aircraft_flags=None):
    now = [98.1]
    state = LiveState(mode='live', clock=lambda: now[0])
    for i in range(count):
        now[0] = 98.1 + i * 1.8 / (count - 1)
        body = bytearray(85)
        body[:16] = b'PRIVATE-POSITION'
        aircraft = bytearray(_synthetic_packet(3, 0x0a, (3, 0x43), i + 1, body))
        if aircraft_flags:
            aircraft[8] = aircraft_flags[i % len(aircraft_flags)]
            aircraft[-2:] = crc16(aircraft[:-2]).to_bytes(2, 'little')
        state.ingest(bytes(aircraft) + synthetic_pose(i + 1))
    now[0] = 100.0
    return state


class BenchEvidenceTests(unittest.TestCase):
    def record(self, state, destination=None):
        recorder = BenchRecorder(state, destination)
        with patch('viewer_server.time.monotonic', return_value=100.0):
            marker = recorder.add({'label': 'Stationary baseline', 'expected_axis': 'baseline'})
        return recorder, marker

    def test_same_packet_pairs_survive_history_private_file_and_export(self):
        state = synthetic_state()
        with tempfile.TemporaryDirectory() as directory:
            recorder, marker = self.record(state, directory)
            saved_path, = Path(directory).glob('*.json')
            self.assertEqual(stat.S_IMODE(saved_path.stat().st_mode), 0o600)
            self.assertEqual(list(Path(directory).glob('*.tmp')), [])
            exported = recorder.export()
            self.assertEqual(json.loads(saved_path.read_text()), exported)
        evidence = exported['markers'][0]['gimbal_sample']['paired_evidence']
        self.assertEqual(evidence['retained_sample_count'], 3)
        self.assertAlmostEqual(evidence['retained_span_s'], 1.8)
        for index, sample in enumerate(evidence['samples'], 1):
            self.assertEqual(sample['source']['sequence'], index)
            self.assertEqual(sample['angles_tenths_raw'][0], index)
            self.assertEqual(struct.unpack('<hhh', bytes.fromhex(sample['field_bytes']['angles_le_hex']))[0], index)
            self.assertEqual(list(struct.unpack('<ffff', bytes.fromhex(sample['field_bytes']['quaternion_le_hex']))), sample['quaternion_fields_sdk_order'])
        self.assertNotEqual(evidence['samples'][0]['quaternion_fields_sdk_order'], evidence['samples'][1]['quaternion_fields_sdk_order'])
        self.assertEqual(evidence['samples'][0]['field_bytes']['quaternion_le_hex'][8:16], '00000080')
        self.assertFalse(evidence['quaternion_component_order_verified'])
        self.assertFalse(evidence['sensor_clock_verified'])
        for secret in ['PRIVATE-ID', b'PRIVATE-ID'.hex(), 'PRIVATE-POSITION', b'PRIVATE-POSITION'.hex()]:
            self.assertNotIn(secret, json.dumps(exported))
        self.assertNotIn('samples', marker['gimbal_sample']['paired_evidence'])
        self.assertNotIn('samples', recorder.snapshot()['markers'][0]['gimbal_sample']['paired_evidence'])
        self.assertEqual(analyze_session(exported)['physical_calibration_verified'], False)
        self.assertEqual(analyze_session(exported)['gimbal_paired_evidence']['retained_pairs_total'], 3)

    def test_bounded_selection_preserves_ends_and_reports_omitted_pairs(self):
        recorder, _ = self.record(synthetic_state(160))
        evidence = recorder.export()['markers'][0]['gimbal_sample']['paired_evidence']
        self.assertEqual(evidence['eligible_sample_count'], 160)
        self.assertEqual(evidence['retained_sample_count'], 128)
        self.assertEqual(evidence['omitted_by_retention_limit'], 32)
        self.assertEqual(evidence['samples'][0]['source']['sequence'], 1)
        self.assertEqual(evidence['samples'][-1]['source']['sequence'], 160)
        self.assertAlmostEqual(evidence['retained_span_s'], 1.8)

    def test_snapshots_and_exports_cannot_mutate_retained_or_baseline_data(self):
        recorder, marker = self.record(synthetic_state())
        marker['gimbal'][0] = 99
        snapshot = recorder.snapshot()
        snapshot['markers'][0]['gimbal_sample']['paired_evidence']['retained_sample_count'] = 999
        exported = recorder.export()
        exported['markers'][0]['gimbal_sample']['paired_evidence']['samples'][0]['quaternion_fields_sdk_order'][0] = 999
        fresh = recorder.export()['markers'][0]
        self.assertNotEqual(fresh['gimbal'][0], 99)
        self.assertEqual(fresh['gimbal_sample']['paired_evidence']['retained_sample_count'], 3)
        self.assertNotEqual(fresh['gimbal_sample']['paired_evidence']['samples'][0]['quaternion_fields_sdk_order'][0], 999)

    def test_source_mixing_or_missing_fields_cannot_create_a_pair(self):
        state = synthetic_state()
        recent = [point for point in state.history_snapshot() if point['kind'] == 'gimbal']
        anchor = state.snapshot()['gimbal']
        bad_points = []
        for field, replacement in [('observer_session_id', 'f' * 16), ('quaternion', [math.nan, 0, 0, 0]),
                                   ('quaternion', [10**1000, 0, 0, 0]), ('timestamp', 10**1000),
                                   ('raw', [999, 0, 0]), ('field_bytes', {}), ('timestamp', 100.1)]:
            bad = copy.deepcopy(recent[0]); bad[field] = replacement; bad_points.append(bad)
        route = copy.deepcopy(recent[0]); route['source']['receiver'] = '8a'; bad_points.append(route)
        evidence = gimbal_pair_evidence(bad_points, anchor['source'], anchor['observer_session_id'], 100.0)
        self.assertFalse(evidence['available'])
        self.assertEqual(evidence['retained_sample_count'], 0)
        self.assertEqual(evidence['omitted_invalid_or_unbound'], len(bad_points))
        missing = gimbal_pair_evidence(recent, anchor['source'], None, 100.0)
        self.assertFalse(missing['available'])

    def test_angle_cohort_does_not_mix_observer_sessions(self):
        state = synthetic_state()
        history = state.history_snapshot()
        for point in history:
            if point['kind'] == 'gimbal' and point['source']['sequence'] == 1:
                point['observer_session_id'] = 'f' * 16
        state.history_snapshot = lambda since=None: copy.deepcopy(history)
        with self.assertRaisesRegex(ValueError, '3 samples'):
            self.record(state)

    def test_history_is_a_detached_copy_and_keeps_fields_from_only_accepted_frames(self):
        state = synthetic_state()
        state.ingest(synthetic_pose(10, quaternion=(math.nan, 0, 0, 0)), timestamp=100.0)
        history = state.history_snapshot()
        self.assertEqual(len([p for p in history if p['kind'] == 'gimbal']), 3)
        history[-1]['quaternion'][0] = 99
        history[-1]['field_bytes']['angles_le_hex'] = 'bad'
        self.assertNotEqual(state.history_snapshot()[-1]['quaternion'][0], 99)
        self.assertNotEqual(state.history_snapshot()[-1]['field_bytes']['angles_le_hex'], 'bad')

    def test_legacy_angle_only_history_stays_explicitly_unavailable(self):
        state = synthetic_state()
        history = state.history_snapshot()
        for point in history:
            point.pop('quaternion', None); point.pop('field_bytes', None)
        state.history_snapshot = lambda since=None: copy.deepcopy(history)
        recorder, _ = self.record(state)
        evidence = recorder.export()['markers'][0]['gimbal_sample']['paired_evidence']
        self.assertFalse(evidence['available'])
        self.assertEqual(evidence['samples'], [])

    def test_supported_fc_ack_modes_share_a_source_cohort(self):
        recorder, marker = self.record(synthetic_state(aircraft_flags=[0, 0x20, 0x40]))
        self.assertEqual(marker['aircraft_sample']['sample_count'], 3)
        self.assertEqual(recorder.export()['markers'][0]['gimbal_sample']['paired_evidence']['retained_sample_count'], 3)

    def test_analysis_rechecks_fields_instead_of_trusting_declared_counts(self):
        recorder, _ = self.record(synthetic_state())
        marker = recorder.export()['markers'][0]
        evidence = marker['gimbal_sample']['paired_evidence']
        evidence['retained_sample_count'] = 999
        evidence['samples'][0]['quaternion_fields_sdk_order'][0] = 123
        checked = summarize_exported_gimbal_pairs(marker)
        self.assertEqual(checked['retained_pairs'], 2)
        self.assertEqual(checked['invalid_pairs'], 1)
        summary = recorder.snapshot()['markers'][0]
        self.assertEqual(summarize_exported_gimbal_pairs(summary)['reason'], 'full_export_required')
        legacy = copy.deepcopy(marker); legacy['gimbal_sample'].pop('paired_evidence')
        self.assertEqual(summarize_exported_gimbal_pairs(legacy)['reason'], 'not_recorded')

    def test_cli_accepts_supported_capacity_instead_of_the_old_five_mib_limit(self):
        recorder = BenchRecorder(synthetic_state(160))
        with patch('viewer_server.time.monotonic', return_value=100.0):
            for index in range(200):
                recorder.add({'label': 'Stationary baseline' if index == 0 else f'SYNTHETIC CAPACITY TEST {index}',
                              'expected_axis': 'baseline'})
        body = json.dumps(recorder.export(), indent=2, allow_nan=False)
        self.assertGreater(len(body.encode()), 5 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'synthetic.json'
            destination = Path(directory) / 'analysis.json'
            source.write_text(body)
            tool = Path(__file__).resolve().parents[1] / 'diagnostics/analyze_bench.py'
            command = [sys.executable, str(tool), str(source), '--reference', 'estimated', '--output', str(destination)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(destination.read_text())
            self.assertEqual(data['recorded_markers'], 200)
            self.assertEqual(data['gimbal_paired_evidence']['retained_pairs_total'], 25600)
            self.assertFalse(data['physical_calibration_verified'])
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            saved = destination.read_bytes()
            repeat = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(repeat.returncode, 2)
            self.assertEqual(destination.read_bytes(), saved)

    def test_bench_reader_rejects_oversized_nonregular_and_symlink_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'session.json'
            source.write_text(json.dumps({'synthetic': 'x' * 64}))
            with self.assertRaisesRegex(ValueError, 'size bound'):
                read_bench_session(source, maximum_bytes=16)
            link = Path(directory) / 'link'
            link.symlink_to(source)
            with self.assertRaises(OSError):
                read_bench_session(link)
            fifo = Path(directory) / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                read_bench_session(fifo)


if __name__ == '__main__':
    unittest.main()
