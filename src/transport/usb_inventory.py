"""Cached USB descriptor normalization and offline comparison; no device writes."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import subprocess


SCHEMA = 'neo2.usb-inventory.v1'
MODULE_STATES = ('installed', 'removed', 'unknown')
POWER_STATES = ('on', 'off', 'usb-only', 'unknown')


def _numbers(value, fields):
    if not isinstance(value, dict):
        raise ValueError('Expected descriptor object')
    result = {}
    for field in fields:
        number = value.get(field)
        maximum = 65535 if field in ('vid', 'pid', 'bcd_usb', 'bcd_device', 'max_packet_size') else 255
        if type(number) is not int or not 0 <= number <= maximum:
            raise ValueError('Invalid or missing descriptor field: ' + field)
        result[field] = number
    return result


def _children(value, field):
    children = value.get(field)
    if not isinstance(children, list):
        raise ValueError('Expected descriptor list: ' + field)
    return children


def normalize_descriptors(raw):
    if not isinstance(raw, dict) or raw.get('mode') != 'cached_descriptors':
        raise ValueError('Expected cached-descriptor helper output')
    if raw.get('errors') != 0 or not isinstance(raw.get('devices'), list):
        raise ValueError('Descriptor observation failed')
    devices = []
    for device in raw['devices']:
        clean = _numbers(device, ('vid', 'pid', 'bcd_usb', 'bcd_device',
                                 'device_class', 'device_subclass', 'device_protocol'))
        if clean['vid'] != 0x2ca3:
            raise ValueError('Unexpected vendor')
        configurations = []
        for cfg in _children(device, 'configurations'):
            config = _numbers(cfg, ('configuration_value', 'configuration_string_index',
                                    'attributes', 'max_power_raw'))
            interfaces = []
            for iface in _children(cfg, 'interfaces'):
                interface = _numbers(iface, ('number', 'alternate', 'class', 'subclass', 'protocol'))
                endpoints = []
                for ep in _children(iface, 'endpoints'):
                    endpoint = _numbers(ep, ('address', 'transfer_type', 'max_packet_size', 'interval_raw'))
                    direction = 'IN' if endpoint['address'] & 128 else 'OUT'
                    if ep.get('direction') != direction:
                        raise ValueError('Endpoint direction disagrees with address')
                    endpoint['direction'] = direction
                    endpoints.append(endpoint)
                interface['endpoints'] = sorted(endpoints, key=lambda ep: ep['address'])
                interfaces.append(interface)
            config['interfaces'] = sorted(interfaces, key=lambda i: (i['number'], i['alternate']))
            configurations.append(config)
        clean['configurations'] = sorted(configurations, key=lambda cfg: cfg['configuration_value'])
        devices.append(clean)
    if raw.get('found') != len(devices):
        raise ValueError('Device count disagrees with helper result')
    return sorted(devices, key=lambda value: json.dumps(value, sort_keys=True))


def collect_inventory(helper, *, module_state='unknown', power_state='unknown'):
    if module_state not in MODULE_STATES or power_state not in POWER_STATES:
        raise ValueError('Unknown physical-state annotation')
    helper = Path(helper).resolve()
    # Widen VID filtering only; remain in cached mode with no device open,
    # interface claim, GET_DESCRIPTOR, bulk I/O, or module configuration.
    try:
        process = subprocess.run([str(helper), '--all-dji'], stdin=subprocess.DEVNULL,
                                 capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('Descriptor helper unavailable or timed out; no inventory conclusion') from exc
    try:
        devices = normalize_descriptors(json.loads(process.stdout))
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Cached descriptor observation failed; no inventory conclusion') from exc
    valid = process.returncode == 0 and bool(devices)
    status = ('observed' if valid else 'inconclusive_no_visible_target'
              if not devices and process.returncode in (0, 3) else 'inconclusive_helper_failure')
    return {'schema': SCHEMA, 'captured_at': dt.datetime.now(dt.timezone.utc).isoformat(),
            'observation_valid': valid,
            'observation_status': status, 'helper_exit_code': process.returncode,
            'method': 'libusb cached descriptor APIs; all DJI product IDs, VID 2ca3',
            'operator_annotations': {'module_state': module_state, 'aircraft_power': power_state},
            'host': {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()},
            'helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
            'devices': devices, 'dji_application_bytes_sent': 0,
            'limits': ['Physical-state annotations are operator reports, not descriptor-derived facts.',
                       'No target visible can reflect sandbox/backend access, not physical absence.',
                       'VID/PID matching does not establish physical unit identity; serials are excluded.',
                       'bcd_device is a USB descriptor revision field, not a verified firmware version.',
                       'Configuration descriptors do not establish the active configuration.',
                       'String contents, bus/address and endpoint traffic are not collected.']}


def compare_inventories(before, after):
    normalized = []
    for snapshot in (before, after):
        if not isinstance(snapshot, dict):
            raise ValueError('Expected inventory object')
        if snapshot.get('schema') != SCHEMA or snapshot.get('observation_valid') is not True:
            raise ValueError('Both observations must be valid; unavailable data is not removal evidence')
        if not isinstance(snapshot.get('devices'), list) or not snapshot['devices']:
            raise ValueError('Missing descriptor inventory')
        annotations = snapshot.get('operator_annotations')
        if not isinstance(annotations, dict):
            raise ValueError('Expected operator annotation object')
        if (annotations.get('module_state') not in MODULE_STATES or
                annotations.get('aircraft_power') not in POWER_STATES):
            raise ValueError('Unknown physical-state annotation')
        normalized.append(normalize_descriptors({'mode': 'cached_descriptors', 'errors': 0,
                                                'found': len(snapshot['devices']),
                                                'devices': snapshot['devices']}))
    changes = []

    def walk(left, right, path):
        if type(left) != type(right):
            changes.append({'path': path, 'before': left, 'after': right})
        elif isinstance(left, dict):
            for key in sorted(left.keys() | right.keys()):
                walk(left.get(key), right.get(key), path + '/' + key)
        elif isinstance(left, list) and len(left) == len(right):
            for index, (a, b) in enumerate(zip(left, right)):
                walk(a, b, path + '/' + str(index))
        elif left != right:
            changes.append({'path': path, 'before': copy.deepcopy(left), 'after': copy.deepcopy(right)})

    walk(*normalized, '/devices')
    a, b = before.get('operator_annotations', {}), after.get('operator_annotations', {})
    power_a, power_b = a.get('aircraft_power'), b.get('aircraft_power')
    state_pair = {a.get('module_state'), b.get('module_state')}
    controlled = (state_pair == {'installed', 'removed'} and power_a == power_b
                  and power_a in ('on', 'off', 'usb-only')
                  and before.get('host') == after.get('host')
                  and isinstance(before.get('host'), dict)
                  and all(isinstance(before['host'].get(key), str) and before['host'][key]
                          for key in ('system', 'release', 'machine'))
                  and before.get('helper_sha256') == after.get('helper_sha256')
                  and isinstance(before.get('helper_sha256'), str)
                  and len(before['helper_sha256']) == 64
                  and all(c in '0123456789abcdef' for c in before['helper_sha256'])
                  and len(before['devices']) == len(after['devices']) == 1)
    return {'schema': 'neo2.usb-inventory-comparison.v1',
            'descriptor_structures_equal': not changes, 'descriptor_changes': changes,
            'reported_conditions_match_installed_removed_pair': controlled,
            'physical_component_ownership_established': False,
            'comparison_is_device_identity_check': False,
            'interpretation': ('No structural difference in the compared descriptors.' if not changes else
                               'Descriptor differences observed; component ownership remains unverified.'),
            'limits': ['Unknown/unequal power, host, helper or ambiguous device counts invalidate a controlled comparison.',
                       'Matching reported conditions do not independently verify the physical handling or USB port.',
                       'An unchanged descriptor does not prove the module is unused.',
                       'Use installed/removed/restored observations before investigating reproducible correlation.',
                       'This comparison does not decode component telemetry or prove USB forwarding.']}
