from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.live_state import LiveState
from transport.live_source import _synthetic_packet


def aircraft_packet(sequence=1, angles=(-123, 456, -789)):
    payload = bytearray(85)
    struct.pack_into('<hhh', payload, 24, *angles)
    return _synthetic_packet(3, 10, (3, 0x43), sequence, payload)


def gimbal_packet(sequence=1):
    payload = bytearray(50)
    struct.pack_into('<hhh', payload, 0, 123, -45, 900)
    struct.pack_into('<ffff', payload, 24, 1, 0, 0, 0)
    return _synthetic_packet(4, 42, (4, 5), sequence, payload)


class LiveStateTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.state = LiveState(clock=lambda: self.now)

    def test_absent_input_never_looks_like_zero_angles(self):
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot['status'], 'starting')
        self.assertIsNone(snapshot['age_ms'])
        self.assertIsNone(snapshot['aircraft'])
        self.assertIsNone(snapshot['gimbal'])

    def test_separate_channels_and_wire_provenance(self):
        self.state.ingest(aircraft_packet() + gimbal_packet())
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot['status'], 'streaming')
        self.assertEqual(snapshot['aircraft']['angles_deg'], [-12.3, 45.6, -78.9])
        self.assertEqual(snapshot['gimbal']['angles_deg'], [12.3, -4.5, 90])
        self.assertEqual(snapshot['aircraft']['source']['receiver'], '0a')
        self.assertEqual(snapshot['gimbal']['source']['receiver'], '2a')
        self.assertEqual(snapshot['gimbal']['quaternion_norm'], 1)
        self.assertEqual(snapshot['transport']['application_bytes_sent'], 0)

    def test_staleness_survives_unknown_fresh_packets(self):
        self.state.ingest(aircraft_packet())
        self.now += 1.1
        self.state.ingest(_synthetic_packet(8, 10, (0, 0x82), 2, b'unknown'))
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot['status'], 'stale')
        self.assertTrue(snapshot['aircraft']['stale'])
        self.assertEqual(snapshot['aircraft']['angles_deg'], [-12.3, 45.6, -78.9])

    def test_each_channel_has_its_own_age(self):
        self.state.ingest(aircraft_packet())
        self.now += 1.5
        self.state.ingest(gimbal_packet())
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot['status'], 'streaming')
        self.assertTrue(snapshot['aircraft']['stale'])
        self.assertFalse(snapshot['gimbal']['stale'])

    def test_crc_bad_data_does_not_refresh_values(self):
        self.state.ingest(aircraft_packet())
        self.now += 2
        bad = bytearray(aircraft_packet(2, (900, 900, 900)))
        bad[-1] ^= 1
        self.state.ingest(bad)
        snapshot = self.state.snapshot()
        self.assertEqual(snapshot['transport']['frames_total'], 1)
        self.assertEqual(snapshot['status'], 'stale')
        self.assertGreater(snapshot['transport']['crc_discarded'], 0)

    def test_usb_splits_keep_partial_without_inventing_a_frame(self):
        raw = aircraft_packet()
        self.state.ingest(raw[:30])
        self.assertIsNone(self.state.snapshot()['aircraft'])
        self.assertEqual(self.state.snapshot()['transport']['pending_bytes'], 30)
        self.state.ingest(raw[30:])
        self.assertEqual(self.state.snapshot()['transport']['frames_total'], 1)

    def test_encrypted_frame_and_incompatible_layout_are_not_decoded(self):
        from transport.duml_observer import crc16
        encrypted = bytearray(aircraft_packet())
        encrypted[8] |= 1
        encrypted[-2:] = crc16(encrypted[:-2]).to_bytes(2, 'little')
        self.state.ingest(encrypted + _synthetic_packet(3, 10, (3, 0x43), 2, bytes(84)))
        snapshot = self.state.snapshot()
        self.assertIsNone(snapshot['aircraft'])
        self.assertEqual(snapshot['transport']['encrypted_frames_ignored'], 1)
        self.assertEqual(snapshot['transport']['layout_rejected'], 1)

    def test_end_and_error_keep_retained_values_marked(self):
        self.state.ingest(aircraft_packet())
        self.state.end()
        self.assertEqual(self.state.snapshot()['status'], 'disconnected')
        self.state.set_error('USB unplugged')
        self.assertEqual(self.state.snapshot()['status'], 'error')
        self.assertEqual(self.state.snapshot()['transport']['last_error'], 'USB unplugged')

    def test_history_is_bounded_copied_and_per_kind(self):
        state = LiveState(clock=lambda: self.now, history_limit=2)
        state.ingest(aircraft_packet() + gimbal_packet())
        self.now += 1
        state.ingest(aircraft_packet(2))
        history = state.history_snapshot(since=100.5)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['kind'], 'aircraft')
        self.assertEqual(history[0]['timestamp'], 101)
        history[0]['angles_deg'][0] = 999
        self.assertNotEqual(state.history_snapshot()[-1]['angles_deg'][0], 999)
        self.assertEqual(len(state.history_snapshot()), 2)

    def test_invalid_timestamps_are_rejected(self):
        self.state.ingest(b'', 100)
        with self.assertRaises(ValueError):
            self.state.ingest(b'', 99)
        with self.assertRaises(ValueError):
            self.state.ingest(b'', float('nan'))


if __name__ == '__main__':
    unittest.main()
