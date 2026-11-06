from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.duml_observer import Frame, crc16
from transport.live_source import _synthetic_packet
from transport.packet_profiles import profile_observations


def packet(receiver=42, payload=b'private-marker', flags=0):
    data = bytearray(_synthetic_packet(4, receiver, (0, 241), 1, payload))
    data[8] = flags
    data[-2:] = crc16(data[:-2]).to_bytes(2, 'little')
    return Frame(bytes(data))


def segment(*frames):
    return {'interface': 4, 'frames': frames}


class PacketProfileTests(unittest.TestCase):
    def test_variation_and_fanout_without_payload_disclosure(self):
        result = profile_observations([segment(packet(), packet(138),
                                               packet(payload=b'private-markes'))])
        first = result['segments'][0]['profiles'][0]
        self.assertEqual(first['frame_count'], 2)
        self.assertEqual(first['payload_variation']['changed_byte_offsets'], [13])
        self.assertEqual(first['payload_variation']['byte_cardinalities'][-1], 2)
        self.assertNotIn('private-marker', json.dumps(result))
        self.assertNotIn(b'private-marker'.hex(), json.dumps(result))
        self.assertEqual(result['segments'][0]['payload_set_fanout'], [])
        matched = profile_observations([segment(packet(), packet(138))])
        fanout = matched['segments'][0]['payload_set_fanout'][0]
        self.assertEqual(fanout['receivers'], ['2a', '8a'])
        self.assertFalse(fanout['packet_timing_or_delivery_pairing_verified'])

    def test_boundaries_flags_and_lengths_are_not_merged(self):
        result = profile_observations([segment(packet()), segment(packet(payload=b'other'))])
        self.assertEqual(len(result['segments']), 2)
        self.assertFalse(result['segments'][0]['profiles'][0]['payload_variation']['variation_assessable'])
        result = profile_observations([segment(packet(), packet(flags=64), packet(payload=b'x'))])
        self.assertEqual(len(result['segments'][0]['profiles']), 3)

    def test_encrypted_data_has_no_plaintext_variation_claim(self):
        result = profile_observations([segment(packet(flags=1), packet(138, flags=1))])
        self.assertTrue(result['segments'][0]['profiles'][0]['encrypted'])
        self.assertIsNone(result['segments'][0]['profiles'][0]['payload_variation'])
        self.assertEqual(result['segments'][0]['payload_set_fanout'], [])

    def test_empty_segment_does_not_invent_component_data(self):
        result = profile_observations([segment()])
        self.assertEqual(result['segments'][0]['frame_count'], 0)
        self.assertEqual(result['segments'][0]['profiles'], [])


if __name__ == '__main__':
    unittest.main()
