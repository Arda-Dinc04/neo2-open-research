import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.usb_inventory import SCHEMA, collect_inventory, compare_inventories, normalize_descriptors


def raw():
    endpoints = [{'address': address, 'direction': direction, 'transfer_type': 2,
                  'max_packet_size': 512, 'interval_raw': 0}
                 for address, direction in ((4, 'OUT'), (133, 'IN'))]
    interface = {'number': 4, 'alternate': 0, 'class': 255, 'subclass': 67,
                 'protocol': 1, 'endpoints': endpoints}
    config = {'configuration_value': 1, 'configuration_string_index': 1,
              'attributes': 128, 'max_power_raw': 250, 'interfaces': [interface]}
    return {'mode': 'cached_descriptors', 'errors': 0, 'found': 1,
            'devices': [{'vid': 0x2ca3, 'pid': 0x20, 'bcd_usb': 512, 'bcd_device': 1284,
                         'device_class': 239, 'device_subclass': 2, 'device_protocol': 1,
                         'bus': 1, 'address': 7, 'serial': 'PRIVATE-SERIAL',
                         'configurations': [config]}]}


def inventory(module='installed', power='on'):
    return {'schema': SCHEMA, 'observation_valid': True,
            'operator_annotations': {'module_state': module, 'aircraft_power': power},
            'host': {'system': 'synthetic', 'release': '1', 'machine': 'test'},
            'helper_sha256': '0' * 64, 'devices': normalize_descriptors(raw())}


class InventoryTests(unittest.TestCase):
    def test_location_serial_and_endpoint_order_do_not_change_structure(self):
        first, second = raw(), raw()
        second['devices'][0]['address'] = 99
        second['devices'][0]['serial'] = 'DIFFERENT-PRIVATE'
        second['devices'][0]['configurations'][0]['interfaces'][0]['endpoints'].reverse()
        self.assertEqual(normalize_descriptors(first), normalize_descriptors(second))
        self.assertNotIn('PRIVATE', json.dumps(normalize_descriptors(first)))
        self.assertNotIn('bus', json.dumps(normalize_descriptors(first)))

    def test_endpoint_change_report_never_claims_physical_ownership(self):
        first, second = inventory(), inventory('removed')
        second['devices'][0]['configurations'][0]['interfaces'][0]['endpoints'][1]['max_packet_size'] = 64
        result = compare_inventories(first, second)
        self.assertFalse(result['descriptor_structures_equal'])
        self.assertTrue(result['reported_conditions_match_installed_removed_pair'])
        self.assertEqual(result['descriptor_changes'][0]['before'], 512)
        self.assertFalse(result['physical_component_ownership_established'])

    def test_unknown_or_changed_conditions_are_not_controlled_pair(self):
        for changed in ('power', 'host', 'helper', 'module', 'count'):
            first, second = inventory(), inventory('removed')
            if changed == 'power': second['operator_annotations']['aircraft_power'] = 'unknown'
            if changed == 'host': second['host']['release'] = '2'
            if changed == 'helper': second['helper_sha256'] = '1' * 64
            if changed == 'module': second['operator_annotations']['module_state'] = 'unknown'
            if changed == 'count': second['devices'] *= 2
            self.assertFalse(compare_inventories(first, second)['reported_conditions_match_installed_removed_pair'])

    def test_invalid_observation_cannot_be_mistaken_for_device_removal(self):
        first, second = inventory(), inventory('removed')
        second['observation_valid'] = False
        second['devices'] = []
        with self.assertRaises(ValueError): compare_inventories(first, second)
        for modified in ({'mode': 'standard_GET_DESCRIPTOR'}, {'errors': 1}, {'found': 2}):
            sample = raw()
            sample.update(modified)
            with self.assertRaises(ValueError): normalize_descriptors(sample)

    def test_invalid_endpoint_direction_or_noninteger_is_rejected(self):
        sample = raw()
        endpoint = sample['devices'][0]['configurations'][0]['interfaces'][0]['endpoints'][1]
        endpoint['direction'] = 'OUT'
        with self.assertRaises(ValueError): normalize_descriptors(sample)
        endpoint['direction'] = 'IN'
        endpoint['address'] = True
        with self.assertRaises(ValueError): normalize_descriptors(sample)

    def test_compare_reapplies_allowlist_to_saved_data(self):
        first, second = inventory(), inventory('removed')
        second['devices'][0]['serial'] = 'DO-NOT-EXPORT'
        result = compare_inventories(first, second)
        self.assertTrue(result['descriptor_structures_equal'])
        self.assertNotIn('DO-NOT-EXPORT', json.dumps(result))

    def test_collector_uses_only_cached_vendor_filter_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'helper'
            helper.write_bytes(b'synthetic helper placeholder')
            process = subprocess.CompletedProcess([str(helper)], 0, json.dumps(raw()), '')
            with patch('transport.usb_inventory.subprocess.run', return_value=process) as run:
                result = collect_inventory(helper)
            self.assertEqual(run.call_args.args[0], [str(helper.resolve()), '--all-dji'])
            self.assertEqual(run.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertNotIn('shell', run.call_args.kwargs)
            self.assertTrue(result['observation_valid'])
            self.assertEqual(result['operator_annotations']['module_state'], 'unknown')
            self.assertEqual(result['dji_application_bytes_sent'], 0)
            self.assertNotIn('PRIVATE-SERIAL', json.dumps(result))

    def test_alternate_dji_product_id_is_not_filtered_out(self):
        sample = raw()
        sample['devices'][0]['pid'] = 0x1234
        self.assertEqual(normalize_descriptors(sample)[0]['pid'], 0x1234)
        sample['devices'][0]['vid'] = 1
        with self.assertRaises(ValueError): normalize_descriptors(sample)

    def test_no_visible_target_remains_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'helper'
            helper.write_bytes(b'synthetic helper placeholder')
            sample = raw()
            sample.update(found=0, devices=[])
            process = subprocess.CompletedProcess([str(helper)], 3, json.dumps(sample), '')
            with patch('transport.usb_inventory.subprocess.run', return_value=process):
                result = collect_inventory(helper)
            self.assertFalse(result['observation_valid'])
            self.assertEqual(result['observation_status'], 'inconclusive_no_visible_target')

    def test_missing_or_hung_helper_does_not_produce_device_absence(self):
        for error in (FileNotFoundError('synthetic missing helper'),
                      subprocess.TimeoutExpired('synthetic helper', 10)):
            with patch('transport.usb_inventory.subprocess.run', side_effect=error):
                with self.assertRaisesRegex(ValueError, 'no inventory conclusion'):
                    collect_inventory('/synthetic/helper')

    def test_helper_failure_with_devices_is_not_no_visible_target(self):
        with tempfile.TemporaryDirectory() as directory:
            helper = Path(directory) / 'helper'
            helper.write_bytes(b'synthetic helper placeholder')
            process = subprocess.CompletedProcess([str(helper)], 3, json.dumps(raw()), '')
            with patch('transport.usb_inventory.subprocess.run', return_value=process):
                result = collect_inventory(helper)
            self.assertFalse(result['observation_valid'])
            self.assertEqual(result['observation_status'], 'inconclusive_helper_failure')
            self.assertEqual(len(result['devices']), 1)
            with self.assertRaises(ValueError): compare_inventories(result, inventory())

    def test_malformed_saved_objects_have_controlled_validation_errors(self):
        for bad in ([], None, 5):
            with self.assertRaises(ValueError): compare_inventories(bad, inventory())
        for annotations in ([], None, {'module_state': 'guessed', 'aircraft_power': 'on'}):
            sample = inventory()
            sample['operator_annotations'] = annotations
            with self.assertRaises(ValueError): compare_inventories(sample, inventory())
        sample = inventory()
        sample['devices'][0]['configurations'] = None
        with self.assertRaises(ValueError): compare_inventories(sample, inventory())


if __name__ == '__main__':
    unittest.main()
