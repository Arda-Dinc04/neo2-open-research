"""Synthetic bytes only; status interpretation never establishes a physical fix."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.component_observer import component_summary, fc_fields
from transport.duml_observer import Frame, crc16
from transport.gnss_status import GnssStatusProfile, gnss_status_candidates
from transport.live_source import _synthetic_packet
from transport.live_state import LiveState


def packet(satellite=0, flags_word=0, *, receiver=10, flags=0, sender=3,
           command=(3, 0x43), length=85):
    payload = bytearray(length)
    payload[:16] = b'PRIVATE-LOCATION'
    payload[32:36] = flags_word.to_bytes(4, 'little')
    payload[36] = satellite
    raw = bytearray(_synthetic_packet(sender, receiver, command, 1, bytes(payload)))
    raw[8] = flags
    raw[-2:] = crc16(raw[:-2]).to_bytes(2, 'little')
    return Frame(bytes(raw))


class GnssStatusTests(unittest.TestCase):
    def test_candidates_ignore_position_and_other_flag_bits(self):
        for word, expected in ((0, False), (0x8000, True), (0xffff7fff, False)):
            values = gnss_status_candidates(packet(17, word).payload)
            self.assertEqual(values, {'satellite_count_byte': 17,
                                     'gps_valid_bit_set': expected, 'physical_fix_verified': False})
            self.assertEqual(fc_fields(packet(17, word).payload)['gnss_status_candidates'], values)
            text = json.dumps(values)
            self.assertNotIn('PRIVATE-LOCATION', text)
            self.assertNotIn('latitude', text)
            self.assertNotIn('longitude', text)

    def test_unknown_layout_and_mutable_payload_are_rejected(self):
        for payload in (bytes(84), bytes(86), bytearray(85), None):
            with self.assertRaises(ValueError):
                gnss_status_candidates(payload)

    def test_empty_and_zero_status_do_not_establish_a_fix(self):
        profile = GnssStatusProfile()
        snapshot = profile.snapshot()
        self.assertEqual(snapshot['cohorts'], [])
        self.assertEqual(snapshot['accepted_frame_occurrences'], 0)
        self.assertFalse(snapshot['physical_fix_verified'])
        profile.observe(packet(), carrier='usb', interface=4)
        cohort = profile.snapshot()['cohorts'][0]
        self.assertEqual(cohort['satellite_count_byte_min'], 0)
        self.assertEqual(cohort['gps_valid_bit_set_occurrences'], 0)
        self.assertFalse(profile.snapshot()['physical_fix_verified'])

    def test_occurrences_extremes_and_routes_are_preserved(self):
        profile = GnssStatusProfile()
        for satellite, word in ((0, 0), (12, 0x8000), (255, 0x8000), (12, 0x8000)):
            profile.observe(packet(satellite, word), carrier='usb', interface=4)
        profile.observe(packet(3, flags=0x20), carrier='usb', interface=4)
        profile.observe(packet(4, receiver=14), carrier='forwarded')
        profile.observe(packet(5, receiver=14), carrier='outer')
        report = profile.snapshot()
        self.assertEqual(report['accepted_frame_occurrences'], 7)
        self.assertEqual(len(report['cohorts']), 4)
        cohort = next(c for c in report['cohorts'] if c['carrier'] == 'usb' and c['flags'] == '00')
        self.assertEqual(cohort['occurrences'], 4)
        self.assertEqual(cohort['satellite_count_byte_min'], 0)
        self.assertEqual(cohort['satellite_count_byte_max'], 255)
        self.assertEqual(cohort['satellite_count_byte_distinct_count'], 3)
        self.assertEqual(cohort['satellite_count_byte_zero_occurrences'], 1)
        self.assertEqual(cohort['gps_valid_bit_set_occurrences'], 3)
        self.assertFalse(report['position_coordinates_exported'])
        self.assertFalse(report['physical_chip_ownership_verified'])

    def test_reply_encryption_wrong_source_command_and_lengths_do_not_contribute(self):
        profile = GnssStatusProfile()
        rejected = [packet(flags=0x80), packet(flags=1), packet(flags=0x60),
                    packet(sender=4), packet(command=(3, 0x55)), packet(length=84), packet(length=86)]
        for frame in rejected:
            self.assertFalse(profile.observe(frame, carrier='usb', interface=4))
        self.assertEqual(profile.snapshot()['accepted_frame_occurrences'], 0)

    def test_unknown_interface_is_explicit_and_does_not_merge_with_known(self):
        profile = GnssStatusProfile()
        profile.observe(packet(), carrier='usb')
        profile.observe(packet(), carrier='usb', interface=4)
        self.assertEqual([c['interface'] for c in profile.snapshot()['cohorts']], [None, 4])
        for carrier, interface in (('fake', 4), ('outer', 4), ('usb', True), ('usb', 256)):
            with self.assertRaises(ValueError):
                profile.observe(packet(), carrier=carrier, interface=interface)

    def test_cohort_cap_fails_and_is_not_hidden_as_a_layout_rejection(self):
        with patch('transport.gnss_status.MAX_GNSS_COHORTS', 1):
            with self.assertRaisesRegex(ValueError, 'gnss_cohort_limit_exceeded'):
                component_summary([{'interface': 4, 'frames': [packet(), packet(receiver=14)]}])

    def test_snapshot_is_detached_from_collector_state(self):
        profile = GnssStatusProfile()
        profile.observe(packet(12, 0x8000), carrier='usb', interface=4)
        old = profile.snapshot()
        old['cohorts'][0]['occurrences'] = 999
        profile.observe(packet(), carrier='usb', interface=4)
        self.assertEqual(profile.snapshot()['accepted_frame_occurrences'], 2)
        self.assertEqual(profile.snapshot()['cohorts'][0]['occurrences'], 2)

    def test_offline_candidates_do_not_expand_live_state_or_bench_history(self):
        state = LiveState(mode='demo', clock=lambda: 10)
        state.ingest(packet(17, 0x8000).raw, timestamp=10)
        snapshot = state.snapshot(10)
        self.assertIsNotNone(snapshot['aircraft'])
        text = json.dumps({'snapshot':snapshot, 'history':state.history_snapshot()})
        for excluded in ('gnss_status', 'gps_valid', 'satellite_count', 'PRIVATE-LOCATION'):
            self.assertNotIn(excluded, text)


if __name__ == '__main__':
    unittest.main()
