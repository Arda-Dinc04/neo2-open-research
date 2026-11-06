from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.duml_observer import Stream, crc8, crc16
from transport.routing_audit import audit, host_address


def frame(sender, receiver, command, sequence):
    # Synthetic analysis-only records; no transport object is involved.
    raw = bytearray([0x55, 13, 4, 0, sender, receiver,
                     sequence & 255, sequence >> 8, 0x80, *command])
    raw[3] = crc8(raw[:3])
    raw.extend(crc16(raw).to_bytes(2, 'little'))
    return Stream().feed(bytes(raw))[0]


class RoutingAuditTests(unittest.TestCase):
    def test_pc_instances_are_preserved(self):
        self.assertEqual([(host_address(a)['type'], host_address(a)['instance'])
                          for a in (0x0a, 0x2a, 0x8a)], [(10, 0), (10, 1), (10, 4)])

    def test_broad_search_finds_reply_rejected_by_strict_match(self):
        frames = [frame(3, 0x2a, (0, 255), 0x8101),
                  frame(0x48, 0x0a, (0, 255), 8),
                  frame(3, 0x0a, (0, 0xfe), 0x8101)]
        result = audit([{'capture': 'synthetic', 'interface': 4, 'frames': frames,
                         'discarded_bytes': 0, 'trailing_partial_bytes': 0}])
        self.assertEqual(result['query_search']['exact_reply_hits'], [])
        self.assertEqual(len(result['query_search']['device_info_any_address_or_sequence']), 2)
        self.assertEqual(len(result['query_search']['query_sequence_any_address_or_command']), 2)

    def test_empty_traffic_cannot_prove_session_setup(self):
        result = audit([])
        self.assertEqual(result['total_frames'], 0)
        self.assertFalse(any(result['possible_session_envelopes'].values()))


if __name__ == '__main__':
    unittest.main()
