from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.component_observer import gimbal_fields, fc_fields, component_summary
from transport.duml_observer import Frame, crc16
from transport.live_source import _synthetic_packet


def frame(payload, flags=0, sender=3, command=(3, 0x43)):
    data = bytearray(_synthetic_packet(sender, 10, command, 1, payload))
    data[8] = flags
    data[-2:] = crc16(data[:-2]).to_bytes(2, 'little')
    return Frame(bytes(data))


class ComponentObserverTests(unittest.TestCase):
    def test_signed_angles_and_quaternion_offsets(self):
        p = bytearray(50)
        struct.pack_into('<hhh', p, 0, -123, 456, -900)
        struct.pack_into('<ffff', p, 24, 1, 0, 0, 0)
        result = gimbal_fields(bytes(p))
        self.assertEqual(result['angles_degrees_sdk_order'], [-12.3, 45.6, -90])
        self.assertEqual(result['quaternion_norm'], 1)
        self.assertFalse(result['physical_reference_frame_verified'])

    def test_unrecognized_layout_and_nonfinite_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            gimbal_fields(bytes(49))
        p = bytearray(50)
        struct.pack_into('<f', p, 24, float('nan'))
        with self.assertRaises(ValueError):
            gimbal_fields(bytes(p))
        with self.assertRaises(ValueError):
            fc_fields(bytes(84))

    def test_fc_export_excludes_position(self):
        p = bytearray(85)
        struct.pack_into('<dd', p, 0, 1.23, 4.56)
        struct.pack_into('<hhh', p, 24, -10, 20, -30)
        result = fc_fields(bytes(p))
        self.assertEqual(result['attitude_degrees_sdk_order'], [-1, 2, -3])
        self.assertNotIn('latitude', result)
        self.assertNotIn('longitude', result)

    def test_no_traffic_does_not_fabricate_battery(self):
        result = component_summary([])
        self.assertEqual(result['gimbal']['frames'], 0)
        self.assertFalse(result['battery']['percentage_available'])
        self.assertIsNone(result['battery']['legacy_osd_byte_40_hypothesis']['mapping_contradicted_by_range'])

    def test_status_bits_remain_unverified_source_candidates(self):
        payload = bytearray(85)
        payload[30] = 0x86
        struct.pack_into('<I', payload, 32, 0x0c)
        fields = fc_fields(bytes(payload))['sdk_status_candidates']
        self.assertEqual(fields['mode_code'], 6)
        self.assertTrue(fields['motors_on_bit'])
        self.assertTrue(fields['flying_pattern'])
        self.assertFalse(fields['physical_state_semantics_verified'])

    def test_legacy_battery_mapping_can_be_contradicted_but_never_auto_validated(self):
        for value, contradicted in ((201, True), (50, False)):
            payload = bytearray(85)
            payload[40] = value
            summary = component_summary([{'frames': [frame(bytes(payload))]}])
            hypothesis = summary['battery']['legacy_osd_byte_40_hypothesis']
            self.assertEqual(hypothesis['mapping_contradicted_by_range'], contradicted)
            self.assertEqual(hypothesis['sample_count'], 1)
            self.assertFalse(hypothesis['mapping_verified'])
            self.assertFalse(summary['battery']['percentage_available'])

    def test_response_packets_are_not_component_observations(self):
        packets = [frame(bytes(85), flags=0x80), frame(bytes(50), flags=0x80, sender=4, command=(4, 5))]
        summary = component_summary([{'frames': packets}])
        self.assertEqual(summary['gimbal']['frames'], 0)
        self.assertEqual(summary['flight_controller_osd']['frames'], 0)
        self.assertEqual(summary['orientation_flags_rejected'], 2)


if __name__ == '__main__':
    unittest.main()
