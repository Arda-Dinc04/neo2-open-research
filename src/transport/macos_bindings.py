"""Summarize existing macOS USB driver trees without exporting registry identifiers."""
import re


def descendants(node):
    children = node.get('IORegistryEntryChildren', [])
    if not isinstance(children, list):
        raise ValueError('Malformed registry children')
    pending = list(children)
    while pending:
        current = pending.pop()
        if not isinstance(current, dict):
            raise ValueError('Malformed registry node')
        yield current
        children = current.get('IORegistryEntryChildren', [])
        if not isinstance(children, list):
            raise ValueError('Malformed registry children')
        pending.extend(children)


def _class(node):
    value = node.get('IOObjectClass')
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,127}', value) else None


def binding_summary(usb_roots, network_roots):
    """Inputs are roots returned by two class-scoped ioreg queries, not all nodes."""
    if not isinstance(usb_roots, list) or not isinstance(network_roots, list):
        raise ValueError('Expected registry root arrays')
    if not all(isinstance(node, dict) for node in usb_roots + network_roots):
        raise ValueError('Expected registry objects')
    network_ids = set()
    for node in network_roots:
        registry_id = node.get('IORegistryEntryID')
        if type(registry_id) is not int:
            raise ValueError('Network registry identity missing; correlation unavailable')
        network_ids.add(registry_id)
    correlation_available = bool(network_ids)

    def network_count(nodes):
        if not correlation_available:
            return None
        return len({node.get('IORegistryEntryID') for node in nodes
                    if node.get('IORegistryEntryID') in network_ids})

    devices = []
    seen_ids = set()
    for root in usb_roots:
        # Only query roots are devices. Interface/driver children often inherit
        # idVendor/idProduct and must never be counted as separate aircraft.
        if root.get('idVendor') != 0x2ca3:
            continue
        product = root.get('idProduct')
        if type(product) is not int or not 0 <= product <= 65535:
            raise ValueError('Invalid USB product ID')
        registry_id = root.get('IORegistryEntryID')
        if type(registry_id) is not int:
            raise ValueError('USB registry identity missing')
        if registry_id in seen_ids:
            continue
        seen_ids.add(registry_id)
        children = list(descendants(root))
        interfaces = []
        for node in children:
            if node.get('IOObjectClass') != 'IOUSBHostInterface':
                continue
            fields = ('bInterfaceNumber', 'bAlternateSetting', 'bInterfaceClass',
                      'bInterfaceSubClass', 'bInterfaceProtocol')
            if not all(type(node.get(field)) is int and 0 <= node[field] <= 255 for field in fields):
                raise ValueError('Incomplete USB interface registry properties')
            attached = list(descendants(node))
            interfaces.append({'number': node['bInterfaceNumber'],
                               'alternate': node['bAlternateSetting'],
                               'class_triplet': [node[field] for field in fields[2:]],
                               'descendant_classes': sorted({name for child in attached
                                                             if (name := _class(child))}),
                               'network_interface_descendants': network_count(attached)})
        active = root.get('kUSBCurrentConfiguration')
        devices.append({'vid': '2ca3', 'pid': f'{product:04x}',
                        'device_class': _class(root),
                        'active_configuration_registry_value': active if type(active) is int else None,
                        'interfaces': sorted(interfaces, key=lambda item: (item['number'], item['alternate'])),
                        'network_interface_descendants': network_count(children)})
    return {'schema': 'neo2.macos-usb-bindings.v1', 'observation_valid': bool(devices),
            'method': 'IOUSBHostDevice and IONetworkInterface IOService registry queries',
            'network_correlation_available': correlation_available,
            'devices': devices, 'device_or_network_probes_sent': False,
            'limits': ['Registry descendants describe host attachment at observation time, not firmware capabilities.',
                       'The two queries are sequential snapshots, not an atomic bus trace.',
                       'An empty network registry leaves correlation unavailable, not a proven negative.',
                       'No visible DJI root can reflect access/backend restrictions, not physical absence.',
                       'No serials, product strings, registry IDs, MAC/IP addresses or BSD interface names are exported.',
                       'No driver installation, network configuration or device/endpoint request is performed.']}
