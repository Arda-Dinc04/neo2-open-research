import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.macos_bindings import binding_summary


def fixture():
    interface = {'IOObjectClass': 'IOUSBHostInterface', 'IORegistryEntryID': 11,
                 'idVendor': 0x2ca3, 'idProduct': 0x20,
                 'bInterfaceNumber': 0, 'bAlternateSetting': 0, 'bInterfaceClass': 224,
                 'bInterfaceSubClass': 1, 'bInterfaceProtocol': 3,
                 'USB Serial Number': 'PRIVATE-SERIAL', 'IORegistryEntryChildren': []}
    return [{'IOObjectClass': 'IOUSBHostDevice', 'IORegistryEntryID': 10,
             'idVendor': 0x2ca3, 'idProduct': 0x20, 'kUSBCurrentConfiguration': 1,
             'USB Product Name': 'PRIVATE-PRODUCT', 'IORegistryEntryChildren': [interface]}]


class MacBindingTests(unittest.TestCase):
    def test_inherited_vendor_properties_do_not_create_multiple_devices(self):
        result = binding_summary(fixture(), [{'IORegistryEntryID': 100}])
        self.assertTrue(result['observation_valid'])
        self.assertEqual(len(result['devices']), 1)
        self.assertEqual(result['devices'][0]['network_interface_descendants'], 0)
        self.assertEqual(result['devices'][0]['interfaces'][0]['descendant_classes'], [])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('IORegistryEntryID', json.dumps(result))

    def test_network_attachment_correlates_ids_without_exporting_identifiers(self):
        usb = fixture()
        usb[0]['IORegistryEntryChildren'][0]['IORegistryEntryChildren'] = [
            {'IOObjectClass': 'SyntheticNetworkDriver', 'IORegistryEntryID': 21,
             'IORegistryEntryChildren': [{'IOObjectClass': 'IOEthernetInterface',
                                          'IORegistryEntryID': 22, 'IOMACAddress': b'private',
                                          'BSD Name': 'en123', 'IPAddress': '192.0.2.1'}]}]
        result = binding_summary(usb, [{'IORegistryEntryID': 22}])
        self.assertEqual(result['devices'][0]['network_interface_descendants'], 1)
        self.assertEqual(result['devices'][0]['interfaces'][0]['network_interface_descendants'], 1)
        self.assertNotIn('en123', json.dumps(result))
        self.assertNotIn('192.0.2.1', json.dumps(result))

    def test_empty_network_registry_does_not_claim_no_attachment(self):
        result = binding_summary(fixture(), [])
        self.assertFalse(result['network_correlation_available'])
        self.assertIsNone(result['devices'][0]['network_interface_descendants'])
        self.assertFalse(binding_summary([], [])['observation_valid'])

    def test_duplicate_query_roots_deduplicate_and_malformed_input_is_rejected(self):
        usb = fixture()
        usb.append(copy.deepcopy(usb[0]))
        self.assertEqual(len(binding_summary(usb, [])['devices']), 1)
        for usb, network in ((None, []), ([], [{}]), ([5], [])):
            with self.assertRaises(ValueError): binding_summary(usb, network)
        usb = fixture()
        usb[0]['IORegistryEntryChildren'][0]['bInterfaceNumber'] = True
        with self.assertRaises(ValueError): binding_summary(usb, [])


if __name__ == '__main__':
    unittest.main()
