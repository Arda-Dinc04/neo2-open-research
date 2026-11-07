"""Synthetic saved datagrams only; these tests have no transport sender."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.duml_observer import crc8, crc16
from transport.wifi_capture_audit import audit_capture, complete_frames, protocol_block


def frame(payload=b'\0' * 10, sender=3, receiver=2, command=(3, 0x55), flags=0):
    head = b'\x55' + ((len(payload) + 13) | 0x400).to_bytes(2, 'little')
    body = head + bytes([crc8(head), sender, receiver]) + b'\x01\0' + bytes([flags, *command]) + payload
    return body + crc16(body).to_bytes(2, 'little')


def datagram(payload, kind=1, slots=0, coded=False):
    if kind == 1:
        tail = bytearray(26 + (slots + 3) // 4)
        tail[20:22] = slots.to_bytes(2, 'little')
        tail[-2:] = len(payload).to_bytes(2, 'little')
    else:
        tail = bytearray(12)
        if coded:
            tail[8:12] = (1 << 14).to_bytes(4, 'little')
    raw = bytearray((0x8000 | (8 + len(tail) + len(payload))).to_bytes(2, 'little') + b'\x11\x22\0\0' + bytes([kind, 0]) + tail + payload)
    for value in raw[:7]:
        raw[7] ^= value
    return bytes(raw)


def row(raw, **extra):
    return {'direction': 'rx', 'interface': 'udp', 'raw_hex': raw.hex(), **extra}


class WifiCaptureAuditTests(unittest.TestCase):
    def audit(self, rows, **options):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'synthetic.jsonl'
            path.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            return audit_capture(path, **options)

    def test_native_forwarding_and_direct_routes_remain_distinct(self):
        inner = frame()
        attributes = bytearray(22)
        attributes[4] = 2
        outer = frame(inner + attributes, sender=0x27, receiver=0xee, command=(0x51, 1))
        result = self.audit([row(datagram(outer)), row(datagram(inner))])
        self.assertEqual(result['counts']['rx_datagrams'], 2)
        self.assertEqual({(r['layer'], r['sender'], r['command']) for r in result['routes']},
                         {('outer', '27', '51/01'), ('forwarded', '03', '03/55'), ('outer', '03', '03/55')})

    def test_exact_bare_inner_compatibility_without_recursive_unwrapping(self):
        nested = frame(frame(), command=(0x51, 1))
        outer = frame(nested, command=(0x51, 1))
        result = self.audit([row(datagram(outer))])
        self.assertEqual(len(result['routes']), 2)
        self.assertTrue(all(r['command'] == '51/01' for r in result['routes']))

    def test_malformed_forwarding_never_scans_for_a_plausible_inner(self):
        for payload in [b'prefix' + frame(), frame() + bytes(21), frame() + bytes(23)]:
            result = self.audit([row(datagram(frame(payload, command=(0x51, 1))))])
            self.assertEqual(result['counts']['invalid_forwarding_envelopes'], 1)
            self.assertEqual(len(result['routes']), 1)
            self.assertEqual(result['routes'][0]['layer'], 'outer')

    def test_corrupt_inner_and_wrong_link_category_are_rejected(self):
        bad = bytearray(frame())
        bad[-1] ^= 1
        attributes = bytearray(22)
        attributes[4] = 2
        for payload in [bad + attributes, frame() + bytes(22)]:
            result = self.audit([row(datagram(frame(payload, command=(0x51, 1))))])
            self.assertEqual(result['counts']['invalid_forwarding_envelopes'], 1)
            self.assertEqual(len(result['routes']), 1)

    def test_encrypted_or_response_carrier_never_becomes_a_push(self):
        for flags in [1, 0x80, 0xc0]:
            result = self.audit([row(datagram(frame(frame(), command=(0x51, 1), flags=flags)))])
            self.assertEqual(len(result['routes']), 1)
            self.assertEqual(result['routes'][0]['flags'], f'{flags:02x}')

    def test_video_coded_fragments_and_tx_cannot_contribute_logical_routes(self):
        result = self.audit([row(datagram(frame(), kind=2)),
                             row(datagram(frame(), kind=3, coded=True)),
                             row(datagram(frame()), direction='tx'),
                             row(datagram(frame()), interface='ble-duml')])
        self.assertEqual(result['routes'], [])
        self.assertEqual(result['counts']['video_skipped'], 1)
        self.assertEqual(result['counts']['coded_protocol_skipped'], 1)

    def test_frames_never_join_across_datagrams_and_duplicates_remain_occurrences(self):
        raw = frame()
        result = self.audit([row(datagram(raw[:8])), row(datagram(raw[8:])),
                             row(datagram(raw)), row(datagram(raw))])
        self.assertEqual(len(result['routes']), 1)
        self.assertEqual(result['routes'][0]['occurrences'], 2)
        self.assertIn('no stream reassembly', result['scope'])

    def test_incomplete_false_header_does_not_hide_later_complete_frame(self):
        head = b'\x55' + (0x400 | 1000).to_bytes(2, 'little')
        self.assertEqual([r.raw for r in complete_frames(head + bytes([crc8(head)]) + frame())], [frame()])

    def test_checksum_length_flags_and_bitmap_must_be_valid(self):
        valid = datagram(frame(), slots=4)
        self.assertEqual(protocol_block(valid)[1], frame())
        for offset in [0, 2, 6, 7]:
            bad = bytearray(valid)
            bad[offset] ^= 1
            with self.assertRaises(ValueError):
                protocol_block(bytes(bad))
        with self.assertRaises(ValueError):
            protocol_block(datagram(frame(), slots=21))
        bad = bytearray(valid)
        bad[33] ^= 1
        with self.assertRaises(ValueError):
            protocol_block(bytes(bad))

    def test_output_omits_raw_values_ids_annotations_and_peer(self):
        result = self.audit([row(datagram(frame(b'private-network')), peer='192.0.2.77',
                                 decoded={'password': 'private-secret'}, session='private-session')])
        text = json.dumps(result)
        for private in ['private-network', '192.0.2.77', 'private-secret', 'private-session', 'raw_hex']:
            self.assertNotIn(private, text)
        self.assertEqual(len(result['source_sha256']), 64)

    def test_symlinks_and_nonregular_files_are_not_capture_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'capture'
            path.write_text('')
            link = Path(directory) / 'link'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                audit_capture(link)
            fifo = Path(directory) / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                audit_capture(fifo)

    def test_structural_profile_tracks_changes_without_exporting_values(self):
        result = self.audit([row(datagram(frame(b'private-a', sender=0x92))),
                             row(datagram(frame(b'private-b', sender=0x92))),
                             row(datagram(frame(b'other-source', sender=3)))], profile_host=0x92)
        variation = result['payload_variation']
        self.assertFalse(variation['payload_values_exported'])
        self.assertEqual(len(variation['profiles']), 1)
        profile = variation['profiles'][0]
        self.assertEqual(profile['distinct_payload_count'], 2)
        self.assertEqual(profile['changed_byte_offsets'], [8])
        self.assertEqual(profile['byte_cardinalities'], [1] * 8 + [2])
        self.assertNotIn('private-a', json.dumps(result))
        self.assertNotIn('707269766174652d61', json.dumps(result))

    def test_fanout_requires_equal_complete_sets_and_matching_layer_flags_layout(self):
        rows = [row(datagram(frame(b'unchanged', sender=0x92, receiver=r))) for r in [2, 0x1c]]
        result = self.audit(rows, profile_host=0x92)['payload_variation']
        self.assertEqual(len(result['payload_set_fanout']), 1)
        self.assertFalse(result['payload_set_fanout'][0]['packet_timing_or_delivery_pairing_verified'])
        rows.append(row(datagram(frame(b'different', sender=0x92, receiver=2))))
        self.assertEqual(self.audit(rows, profile_host=0x92)['payload_variation']['payload_set_fanout'], [])
        encrypted = self.audit([row(datagram(frame(b'cipher', sender=0x92, flags=1)))], profile_host=0x92)
        self.assertEqual(encrypted['payload_variation']['profiles'], [])

    def test_capped_distinct_counts_are_explicit_and_cannot_establish_fanout(self):
        rows = [row(datagram(frame(bytes([v]), sender=0x92, receiver=r))) for r in [2, 0x1c] for v in range(4)]
        with patch('transport.wifi_capture_audit.MAX_DISTINCT_PAYLOADS', 2):
            variation = self.audit(rows, profile_host=0x92)['payload_variation']
        for profile in variation['profiles']:
            self.assertIsNone(profile['distinct_payload_count'])
            self.assertEqual(profile['distinct_payload_count_lower_bound'], 3)
            self.assertTrue(profile['distinct_count_capped'])
            self.assertEqual(profile['byte_cardinalities'], [4])
        self.assertEqual(variation['payload_set_fanout'], [])

    def test_profile_limits_fail_instead_of_accumulating_unbounded_state(self):
        rows = [row(datagram(frame(sender=0x92, receiver=r))) for r in [2, 0x1c]]
        with patch('transport.wifi_capture_audit.MAX_PROFILE_ROUTES', 1):
            with self.assertRaisesRegex(ValueError, 'profile_limit'):
                self.audit(rows, profile_host=0x92)
        for invalid in [True, -1, 256, '92']:
            with self.assertRaisesRegex(ValueError, 'logical_byte'):
                self.audit([], profile_host=invalid)


if __name__ == '__main__':
    unittest.main()
