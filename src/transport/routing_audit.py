"""Offline route census and broad reply search; no transport or transmit I/O."""
from collections import Counter, defaultdict
import json
from pathlib import Path

from .duml_observer import Stream


def host_address(value):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError('DUML address must be one byte')
    kind, instance = value & 31, value >> 5
    # Legacy source enum labels are hints, not proof of physical components.
    labels = {3: 'flight-controller (legacy type label)',
              4: 'gimbal (legacy type label)',
              8: 'air-side processor (legacy type label)',
              10: 'PC (legacy type label)',
              18: 'vision processor (legacy type label)'}
    return {'wire_hex': f'{value:02x}', 'type': kind, 'instance': instance,
            'source_label': labels.get(kind, 'unassigned here')}


def read_capture(path):
    data = json.loads(Path(path).read_text())
    observations = data.get('observations')
    if observations is None:
        fields = ('preflight_rx_hex', 'response_rx_hex')
        if not any(name in data for name in fields):
            raise ValueError('Expected raw receive-only or query capture')
        observations = [{'interface': data.get('interface', 4),
                         'chunks': [{'hex': data[name]} for name in fields if name in data]}]
    result = []
    for observation in observations:
        stream, frames = Stream(), []
        for chunk in observation.get('chunks', []):
            frames.extend(stream.feed(bytes.fromhex(chunk['hex'])))
        result.append({'capture': Path(path).name,
                       'interface': observation['interface'], 'frames': frames,
                       'discarded_bytes': stream.discarded,
                       'trailing_partial_bytes': len(stream.buffer)})
    return result


def audit(observations, sequence=0x8101):
    observations = list(observations)
    counts = Counter()
    lengths = defaultdict(set)
    flags = Counter()
    sequence_hits = []
    identity_hits = []
    exact_hits = []
    all_addresses = set()
    for observation in observations:
        for frame in observation['frames']:
            key = (observation['interface'], frame.sender, frame.receiver,
                   frame.command[0], frame.command[1])
            counts[key] += 1
            lengths[key].add(len(frame.payload))
            flags[frame.raw[8]] += 1
            all_addresses.update((frame.sender, frame.receiver))
            hit = {'capture': observation['capture'], 'interface': observation['interface'],
                   'sender': host_address(frame.sender), 'receiver': host_address(frame.receiver),
                   'command': f'{frame.command[0]:02x}/{frame.command[1]:02x}',
                   'sequence': frame.sequence, 'flags_hex': f'{frame.raw[8]:02x}'}
            if frame.sequence == sequence:
                sequence_hits.append(hit)
            if frame.command == (0, 255):
                identity_hits.append(hit)
                if frame.sequence == sequence and frame.sender == 3 and frame.receiver == 10:
                    exact_hits.append(hit)
    return {
        'scope': 'offline, CRC-valid received DUML frames only; no packet transmissions',
        'total_frames': sum(counts.values()),
        'addresses': [host_address(a) for a in sorted(all_addresses)],
        'routes': [{'interface': key[0], 'sender': host_address(key[1]),
                    'receiver': host_address(key[2]), 'command': f'{key[3]:02x}/{key[4]:02x}',
                    'count': count, 'payload_lengths': sorted(lengths[key])}
                   for key, count in sorted(counts.items())],
        'flags': {f'{flag:02x}': count for flag, count in sorted(flags.items())},
        'encrypted_frames': sum(n for flag, n in flags.items() if flag & 7),
        'response_flag_frames': sum(n for flag, n in flags.items() if flag & 128),
        'query_search': {'sequence_hex': f'{sequence:04x}',
                         'exact_reply_hits': exact_hits,
                         'device_info_any_address_or_sequence': identity_hits,
                         'query_sequence_any_address_or_command': sequence_hits},
        'possible_session_envelopes': {
            name: sum(n for key, n in counts.items() if key[3:] == command)
            for name, command in {'51/01_forwarded': (0x51, 1),
                                  '00/99_subscription_agent': (0, 0x99),
                                  '07/93_wifi_registration': (7, 0x93)}.items()},
        'capture_boundaries': [{'capture': o['capture'], 'interface': o['interface'],
                               'frames': len(o['frames']), 'discarded_bytes': o['discarded_bytes'],
                               'trailing_partial_bytes': o['trailing_partial_bytes']}
                              for o in observations],
        'limits': ['Addresses identify logical type and instance, not physical chip ownership.',
                   'Idle RX captures do not establish the host TX/session-initialization sequence.',
                   'Absence of a reply does not distinguish command support, routing, or session policy.'],
    }
