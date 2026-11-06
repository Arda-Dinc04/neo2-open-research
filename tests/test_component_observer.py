from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.component_observer import gimbal_fields, fc_fields, component_summary


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


if __name__ == '__main__':
    unittest.main()
