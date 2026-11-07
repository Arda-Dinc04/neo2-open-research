"""Offline FC GNSS status candidates; never decode or export position bytes.

Field evidence is the pinned telemetry.py listed in docs/gnss-status-findings.md.
These candidates do not establish a fix, physical accuracy or chip ownership.
Callers supply CRC-validated DUML frames from the existing receive-file parsers.
"""

MAX_GNSS_COHORTS = 64


def gnss_status_candidates(payload):
    if not isinstance(payload, bytes) or len(payload) != 85:
        raise ValueError('gnss_requires_observed_85_byte_fc_layout')
    return {
        'satellite_count_byte': payload[36],
        'gps_valid_bit_set': bool(int.from_bytes(payload[32:36], 'little') & 0x8000),
        'physical_fix_verified': False,
    }


class GnssStatusProfile:
    """Bounded occurrence counts, separated by carrier/interface/route/flags."""

    def __init__(self):
        self._groups = {}

    def observe(self, frame, *, carrier, interface=None):
        if carrier not in ('usb', 'outer', 'forwarded'):
            raise ValueError('unsupported_gnss_carrier')
        if ((interface is not None and (type(interface) is not int or not 0 <= interface <= 255))
                or (carrier != 'usb' and interface is not None)):
            raise ValueError('invalid_gnss_interface')
        if (frame.sender != 3 or frame.command != (3, 0x43)
                or frame.raw[8] not in (0, 0x20, 0x40) or len(frame.payload) != 85):
            return False
        values = gnss_status_candidates(frame.payload)
        key = (carrier, -1 if interface is None else interface, frame.receiver, frame.raw[8])
        if key not in self._groups:
            if len(self._groups) >= MAX_GNSS_COHORTS:
                raise ValueError('gnss_cohort_limit_exceeded')
            self._groups[key] = {'occurrences': 0, 'gps_valid_bit_set_occurrences': 0,
                                 'satellite_count_byte_min': 255, 'satellite_count_byte_max': 0,
                                 'satellite_count_byte_zero_occurrences': 0, '_seen': 0}
        group = self._groups[key]
        satellite = values['satellite_count_byte']
        group['occurrences'] += 1
        group['gps_valid_bit_set_occurrences'] += int(values['gps_valid_bit_set'])
        group['satellite_count_byte_min'] = min(group['satellite_count_byte_min'], satellite)
        group['satellite_count_byte_max'] = max(group['satellite_count_byte_max'], satellite)
        group['satellite_count_byte_zero_occurrences'] += int(satellite == 0)
        group['_seen'] |= 1 << satellite
        return True

    def snapshot(self):
        cohorts = []
        for (carrier, interface, receiver, flags), group in sorted(self._groups.items()):
            cohorts.append({
                'carrier': carrier, 'interface': None if interface == -1 else interface, 'sender': '03',
                'receiver': f'{receiver:02x}', 'command': '03/43',
                'flags': f'{flags:02x}', 'payload_length': 85,
                **{key: value for key, value in group.items() if key != '_seen'},
                'satellite_count_byte_distinct_count': group['_seen'].bit_count(),
            })
        return {
            'schema': 'neo2.gnss-status-profile.v1',
            'mode': 'offline_saved_capture',
            'accepted_frame_occurrences': sum(c['occurrences'] for c in cohorts),
            'cohorts': cohorts,
            'layout': {'payload_length': 85, 'satellite_count_offset_bytes': 36,
                       'gps_flags_offset_bytes': 32, 'gps_flags_length_bytes': 4,
                       'gps_flags_mask_hex': '00008000'},
            'position_coordinates_exported': False,
            'physical_fix_verified': False,
            'physical_chip_ownership_verified': False,
            'limits': ['Source-backed field candidates, not validated GNSS capability.',
                       'Occurrences are not deduplicated sensor measurements.',
                       'Satellite byte 255 is retained without guessing a sentinel.',
                       'GPS bit alone is not the SDK location-availability condition.'],
        }
