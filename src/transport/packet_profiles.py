"""Structural profiles of validated saved frames; never export payload values."""
from collections import defaultdict


def profile_observations(observations):
    """Keep capture boundaries separate: no gap/rate or physical owner inference."""
    segments = []
    for index, observation in enumerate(observations):
        groups = defaultdict(list)
        for frame in observation['frames']:
            key = (frame.sender, frame.receiver, *frame.command,
                   frame.raw[8], len(frame.payload))
            groups[key].append(frame.payload)
        profiles = []
        for key, payloads in sorted(groups.items()):
            sender, receiver, command_set, command_id, flags, length = key
            encrypted = bool(flags & 7)
            variations = ([len({payload[offset] for payload in payloads})
                           for offset in range(length)] if not encrypted else None)
            profiles.append({
                'sender': f'{sender:02x}', 'receiver': f'{receiver:02x}',
                'command': f'{command_set:02x}/{command_id:02x}',
                'flags_hex': f'{flags:02x}', 'encrypted': encrypted,
                'payload_length': length, 'frame_count': len(payloads),
                'payload_variation': None if encrypted else {
                    'distinct_payload_count': len(set(payloads)),
                    'changed_byte_offsets': [i for i, count in enumerate(variations) if count > 1],
                    'byte_cardinalities': variations,
                    'variation_assessable': len(payloads) >= 2,
                },
            })
        # Same command/content delivered to multiple logical receivers is an
        # observation of fan-out, not proof of who generates or owns that data.
        fanout = []
        for left_index, left in enumerate(sorted(groups)):
            for right in sorted(groups)[left_index + 1:]:
                if left[1] == right[1] or left[0:1] + left[2:] != right[0:1] + right[2:]:
                    continue
                if left[4] & 7:
                    continue
                left_payloads, right_payloads = set(groups[left]), set(groups[right])
                if left_payloads == right_payloads:
                    fanout.append({'sender': f'{left[0]:02x}',
                                   'receivers': [f'{left[1]:02x}', f'{right[1]:02x}'],
                                   'command': f'{left[2]:02x}/{left[3]:02x}',
                                   'payload_length': left[5],
                                   'observed_payload_sets_equal': True,
                                   'packet_timing_or_delivery_pairing_verified': False})
        segments.append({'segment_index': index, 'interface': observation['interface'],
                         'frame_count': sum(len(values) for values in groups.values()),
                         'discarded_bytes': observation.get('discarded_bytes', 0),
                         'trailing_partial_bytes': observation.get('trailing_partial_bytes', 0),
                         'profiles': profiles, 'payload_set_fanout': fanout})
    return {'schema': 'neo2.packet-profiles.v1', 'segments': segments,
            'scope': 'offline CRC-validated receive frames, grouped within each capture segment',
            'payload_values_exported': False, 'device_io_performed': False,
            'limits': ['Constant bytes in an idle window do not establish field semantics or unused sensors.',
                       'Cardinalities and changed offsets do not identify units, clocks, counters or component ownership.',
                       'Encrypted payload bytes are not profiled as plaintext.',
                       'Timing, sample rates and sequence-loss estimates are not inferred across capture boundaries.',
                       'This structural report still requires review before publication.']}
