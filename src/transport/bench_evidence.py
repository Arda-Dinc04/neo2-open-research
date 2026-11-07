"""Bounded same-packet gimbal evidence for private bench exports only."""
import math
import re
import struct

GIMBAL_PAIR_SCHEMA = 'neo2.gimbal-paired-evidence.v1'
MAX_GIMBAL_PAIRS = 128
WINDOW_SECONDS = 2.0


def finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def finite_vector(value, size):
    return isinstance(value, list) and len(value) == size and all(finite_number(item) for item in value)


def route_key(source):
    if not isinstance(source, dict):
        return None
    required = ('sender', 'receiver', 'command', 'flags_hex', 'payload_length')
    if not all(name in source for name in required):
        return None
    # The FC's supported push ACK modes do not create different source routes.
    return tuple(source[name] for name in ('sender', 'receiver', 'command', 'payload_length'))


def gimbal_pair_evidence(recent, anchor, observer_session_id, now, *, limit=MAX_GIMBAL_PAIRS):
    """Keep observed float fields in their recorded order, never average/normalize.

    Recheck bytes against decoded fields so a current quaternion cannot be
    attached to older Euler samples. No camera/sensor clock or physical frame
    is inferred from the PC receipt timestamp.
    """
    if type(limit) is not int or not 2 <= limit <= MAX_GIMBAL_PAIRS:
        raise ValueError('Invalid paired-evidence bound')
    samples = []
    session_valid = (isinstance(observer_session_id, str)
                     and re.fullmatch('[0-9a-f]{16}', observer_session_id))
    for point in recent:
        source = point.get('source')
        stamp = point.get('timestamp')
        if (not session_valid or point.get('observer_session_id') != observer_session_id
                or point.get('kind') != 'gimbal' or route_key(source) != route_key(anchor)
                or route_key(source) is None
                or source['sender'] != '04' or source['command'] != '04/05'
                or source['flags_hex'] != '00' or source['payload_length'] != 50
                or not isinstance(source['receiver'], str)
                or not re.fullmatch('[0-9a-f]{2}', source['receiver'])
                or type(source.get('sequence')) is not int or not 0 <= source['sequence'] <= 65535
                or not finite_number(stamp)
                or not now - WINDOW_SECONDS <= stamp <= now
                or not finite_vector(point.get('angles_deg'), 3)
                or not finite_vector(point.get('quaternion'), 4)):
            continue
        fields = point.get('field_bytes')
        raw = point.get('raw')
        if (not isinstance(fields, dict) or not isinstance(raw, list) or len(raw) != 3
                or not all(type(value) is int and -32768 <= value <= 32767 for value in raw)):
            continue
        angles_hex, quaternion_hex = fields.get('angles_le_hex'), fields.get('quaternion_le_hex')
        if (not isinstance(angles_hex, str) or not re.fullmatch('[0-9a-f]{12}', angles_hex)
                or not isinstance(quaternion_hex, str) or not re.fullmatch('[0-9a-f]{32}', quaternion_hex)):
            continue
        raw_angles = list(struct.unpack('<hhh', bytes.fromhex(angles_hex)))
        quaternion = list(struct.unpack('<ffff', bytes.fromhex(quaternion_hex)))
        if (not finite_vector(quaternion, 4) or point.get('raw') != raw_angles
                or point['angles_deg'] != [value / 10 for value in raw_angles]
                or point['quaternion'] != quaternion):
            continue
        samples.append({'receipt_offset_s': stamp - now,
            'angles_tenths_raw': raw_angles, 'angles_deg_sdk_order': list(point['angles_deg']),
            'quaternion_fields_sdk_order': quaternion,
            'quaternion_norm': math.sqrt(sum(value * value for value in quaternion)),
            'field_bytes': {'angles_le_hex': angles_hex, 'quaternion_le_hex': quaternion_hex},
            'source': {name: source[name] for name in ('sender', 'receiver', 'command', 'sequence', 'flags_hex', 'payload_length')}})
    samples.sort(key=lambda sample: sample['receipt_offset_s'])
    eligible = len(samples)
    if eligible > limit:
        samples = [samples[index * (eligible - 1) // (limit - 1)] for index in range(limit)]
    return {'schema': GIMBAL_PAIR_SCHEMA,
        'available': bool(samples), 'pairing_basis': 'Euler and quaternion fields from one accepted gimbal packet',
        'receipt_time_basis': 'PC monotonic; offsets relative to marker collection',
        'observer_session_id': observer_session_id if session_valid else None,
        'requested_window_s': WINDOW_SECONDS, 'maximum_retained_samples': limit,
        'eligible_sample_count': eligible, 'retained_sample_count': len(samples),
        'omitted_invalid_or_unbound': len(recent) - eligible,
        'omitted_by_retention_limit': max(0, eligible - limit),
        'selection': 'all eligible samples' if eligible <= limit else 'uniform indices including first and last',
        'retained_span_s': samples[-1]['receipt_offset_s'] - samples[0]['receipt_offset_s'] if samples else 0,
        'source_field_layout': {'angles_offset_bytes': 0, 'angles_length_bytes': 6,
                                'quaternion_offset_bytes': 24, 'quaternion_length_bytes': 16},
        'quaternion_component_order_verified': False, 'physical_reference_frame_verified': False,
        'sensor_clock_verified': False, 'complete_bus_capture': False,
        'samples': samples}


def summarize_exported_gimbal_pairs(marker):
    """Check a private full export structurally; counts confer no calibration."""
    channel = marker.get('gimbal_sample', {})
    evidence = channel.get('paired_evidence') if isinstance(channel, dict) else None
    summary = {'available': False, 'retained_pairs': 0, 'invalid_pairs': 0,
               'retained_span_s': 0, 'reason': 'not_recorded'}
    if not isinstance(evidence, dict):
        return summary
    if evidence.get('schema') != GIMBAL_PAIR_SCHEMA:
        return {**summary, 'reason': 'unsupported_evidence_schema'}
    rows = evidence.get('samples')
    if not isinstance(rows, list):
        return {**summary, 'reason': 'full_export_required'}
    if len(rows) > MAX_GIMBAL_PAIRS:
        return {**summary, 'reason': 'evidence_sample_limit_exceeded'}
    points = [{'kind': 'gimbal', 'timestamp': row.get('receipt_offset_s'),
               'angles_deg': row.get('angles_deg_sdk_order'), 'raw': row.get('angles_tenths_raw'),
               'quaternion': row.get('quaternion_fields_sdk_order'), 'field_bytes': row.get('field_bytes'),
               'source': row.get('source'), 'observer_session_id': evidence.get('observer_session_id')}
              for row in rows if isinstance(row, dict)]
    checked = gimbal_pair_evidence(points, channel.get('source'), evidence.get('observer_session_id'), 0.0)
    count = checked['retained_sample_count']
    return {**summary, 'available': count > 0, 'retained_pairs': count,
            'invalid_pairs': len(rows) - count, 'retained_span_s': checked['retained_span_s'],
            'reason': 'paired_fields_present' if count else 'no_valid_pairs'}
