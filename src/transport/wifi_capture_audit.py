"""Offline header census of complete DUML frames in saved SWUDP datagrams.

This has no sockets, device handles, application encoders or session owner.
It does not reconstruct reliable streams, recover FEC or deduplicate traffic.
Wire-layout evidence: the pinned upstream transport.py and wlm_discovery.py
listed in docs/wifi-route-findings.md.
"""
from collections import Counter
import hashlib
import json
import os
import stat

from .duml_observer import Frame, crc8, crc16

MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_LINE_BYTES = 65536
MAX_RECORDS = 1000000
MAX_ROUTES = 4096
MAX_PROFILE_ROUTES = 64
MAX_PROFILE_POSITIONS = 32768
MAX_DISTINCT_PAYLOADS = 128


def complete_frames(data):
    """Find CRC-valid, non-overlapping frames contained entirely in one block."""
    offset = 0
    while offset + 13 <= len(data):
        if data[offset] != 0x55:
            offset += 1
            continue
        header = data[offset:offset + 4]
        tag = int.from_bytes(header[1:3], 'little')
        size = tag & 0x3ff
        if (tag >> 10 != 1 or not 13 <= size <= 1023
                or crc8(header[:3]) != header[3] or offset + size > len(data)):
            offset += 1
            continue
        raw = data[offset:offset + size]
        if crc16(raw[:-2]) != int.from_bytes(raw[-2:], 'little'):
            offset += 1
            continue
        yield Frame(raw)
        offset += size


def protocol_block(raw):
    """Validate the pinned ACK-mode-1 envelope needed for this frame census."""
    if not 8 <= len(raw) <= 1472:
        raise ValueError('invalid_swudp_length')
    word = int.from_bytes(raw[:2], 'little')
    checksum = 0
    for value in raw[:7]:
        checksum ^= value
    if word & 0x3fff != len(raw) or word >> 14 != 2 or checksum != raw[7]:
        raise ValueError('invalid_swudp_header')
    kind = raw[6]
    if kind == 1:
        if len(raw) < 34:
            raise ValueError('truncated_swudp_status')
        slots = int.from_bytes(raw[28:30], 'little')
        if slots > 20:
            raise ValueError('unsupported_swudp_ack_window')
        offset = 34 + (slots + 3) // 4
        if offset > len(raw) or int.from_bytes(raw[offset - 2:offset], 'little') != len(raw) - offset:
            raise ValueError('invalid_swudp_aggregate')
        return 'status', raw[offset:]
    if kind == 3:
        if len(raw) < 20:
            raise ValueError('truncated_swudp_protocol')
        if int.from_bytes(raw[16:20], 'little') & (1 << 14):
            return 'coded_protocol_skipped', b''
        return 'protocol_fragment', raw[20:]
    return 'video_skipped' if kind == 2 else 'other_transport_skipped', b''


def forwarded_frame(outer):
    """One exact plaintext 51/01 inner frame; never search a malformed trailer."""
    if outer.command != (0x51, 1) or outer.raw[8] not in (0, 0x20, 0x40):
        return None
    payload = outer.payload
    if not 13 <= len(payload) <= 1010:
        raise ValueError('invalid_forwarding_length')
    size = int.from_bytes(payload[1:3], 'little') & 0x3ff
    if len(payload) == size:
        inner = payload
    elif len(payload) == size + 22:
        if payload[size + 4] & 15 != 2:
            raise ValueError('unsupported_forwarding_link_category')
        inner = payload[:size]
    else:
        raise ValueError('invalid_forwarding_trailer')
    frames = list(complete_frames(inner))
    if len(frames) != 1 or frames[0].raw != inner:
        raise ValueError('invalid_forwarded_frame')
    return frames[0]


def audit_capture(path, *, profile_host=None):
    """Return counts and a private reproducibility digest, never payloads or IDs."""
    if profile_host is not None and (type(profile_host) is not int or not 0 <= profile_host <= 255):
        raise ValueError('profile_host_must_be_logical_byte')
    counters, routes = Counter(), Counter()
    profiles = {}
    positions = 0
    digest = hashlib.sha256()
    total = 0
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError('capture_must_be_bounded_regular_file')
        while line := source.readline(MAX_LINE_BYTES + 1):
            counters['records'] += 1
            total += len(line)
            if (len(line) > MAX_LINE_BYTES or total > MAX_FILE_BYTES
                    or counters['records'] > MAX_RECORDS):
                raise ValueError('capture_read_limit_exceeded')
            digest.update(line)
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError
                if row.get('direction') != 'rx' or row.get('interface') != 'udp':
                    counters['non_udp_rx_records_skipped'] += 1
                    continue
                text = row.get('raw_hex')
                if not isinstance(text, str) or len(text) > 2944:
                    raise ValueError
                raw = bytes.fromhex(text)
            except (ValueError, TypeError):
                counters['invalid_records'] += 1
                continue
            counters['rx_datagrams'] += 1
            try:
                kind, block = protocol_block(raw)
            except ValueError:
                counters['invalid_transport_envelopes'] += 1
                continue
            counters[kind] += 1
            for outer in complete_frames(block):
                packets = [('outer', outer)]
                try:
                    child = forwarded_frame(outer)
                    if child is not None:
                        packets.append(('forwarded', child))
                except ValueError:
                    counters['invalid_forwarding_envelopes'] += 1
                for layer, packet in packets:
                    key = (layer, packet.sender, packet.receiver, *packet.command,
                           packet.raw[8], len(packet.payload))
                    routes[key] += 1
                    if len(routes) > MAX_ROUTES:
                        raise ValueError('capture_route_limit_exceeded')
                    if packet.sender != profile_host or packet.raw[8] & 7:
                        continue
                    if key not in profiles:
                        positions += len(packet.payload)
                        if len(profiles) >= MAX_PROFILE_ROUTES or positions > MAX_PROFILE_POSITIONS:
                            raise ValueError('capture_profile_limit_exceeded')
                        profiles[key] = {'bytes': [0] * len(packet.payload), 'digests': set(), 'capped': False}
                    profile = profiles[key]
                    for offset, value in enumerate(packet.payload):
                        profile['bytes'][offset] |= 1 << value
                    payload_digest = hashlib.sha256(packet.payload).digest()
                    if payload_digest not in profile['digests']:
                        if len(profile['digests']) < MAX_DISTINCT_PAYLOADS:
                            profile['digests'].add(payload_digest)
                        else:
                            profile['capped'] = True
        after = os.fstat(source.fileno())
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError('capture_changed_during_audit')
    def route(key, count):
        return {'layer': key[0], 'sender': f'{key[1]:02x}', 'receiver': f'{key[2]:02x}',
                'command': f'{key[3]:02x}/{key[4]:02x}', 'flags': f'{key[5]:02x}',
                'payload_length': key[6], 'occurrences': count}
    variations = []
    for key, profile in sorted(profiles.items()):
        cardinalities = [value.bit_count() for value in profile['bytes']]
        variations.append({**route(key, routes[key]),
            'distinct_payload_count': None if profile['capped'] else len(profile['digests']),
            'distinct_payload_count_lower_bound': len(profile['digests']) + int(profile['capped']),
            'distinct_count_capped': profile['capped'],
            'changed_byte_offsets': [i for i, count in enumerate(cardinalities) if count > 1],
            'byte_cardinalities': cardinalities, 'variation_assessable': routes[key] >= 2})
    fanout = []
    keys = sorted(profiles)
    for index, left in enumerate(keys):
        for right in keys[index + 1:]:
            if left[2] == right[2] or left[:2] + left[3:] != right[:2] + right[3:]:
                continue
            a, b = profiles[left], profiles[right]
            if not a['capped'] and not b['capped'] and a['digests'] == b['digests']:
                fanout.append({'layer': left[0], 'sender': f'{left[1]:02x}',
                    'receivers': [f'{left[2]:02x}', f'{right[2]:02x}'],
                    'command': f'{left[3]:02x}/{left[4]:02x}', 'flags': f'{left[5]:02x}',
                    'payload_length': left[6], 'observed_payload_sets_equal': True,
                    'packet_timing_or_delivery_pairing_verified': False})
    return {'schema': 'neo2.wifi-route-audit.v1', 'mode': 'offline_saved_capture',
            'transport_profile': 'neo2_swudp_ack_mode_1_complete_frames',
            'source_sha256': digest.hexdigest(), 'counts': dict(counters),
            'scope': 'complete CRC-valid frame occurrences; no stream reassembly, FEC recovery, deduplication or physical ownership inference',
            'routes': [route(key, count) for key, count in sorted(routes.items())],
            'payload_variation': {'profile_host': None if profile_host is None else f'{profile_host:02x}',
                'payload_values_exported': False, 'maximum_profiles': MAX_PROFILE_ROUTES,
                'maximum_profiled_byte_positions': MAX_PROFILE_POSITIONS,
                'maximum_distinct_payloads_per_profile': MAX_DISTINCT_PAYLOADS,
                'profiles': variations, 'payload_set_fanout': fanout}}
