"""Analyze saved operator annotations without hardware I/O or calibration writes."""
import json
import os
import stat

from .bench_evidence import finite_vector, summarize_exported_gimbal_pairs

MAX_BENCH_FILE_BYTES = 64 * 1024 * 1024


def read_bench_session(path, *, maximum_bytes=MAX_BENCH_FILE_BYTES):
    """Read one immutable, bounded regular export; never follow a FIFO/symlink."""
    if type(maximum_bytes) is not int or not 1 <= maximum_bytes <= MAX_BENCH_FILE_BYTES:
        raise ValueError('Invalid bench input bound')
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum_bytes:
            raise ValueError('Bench input must be a regular file within the size bound')
        body = source.read(maximum_bytes + 1)
        after = os.fstat(source.fileno())
    if len(body) > maximum_bytes:
        raise ValueError('Bench input exceeds the size bound')
    if any(getattr(before, field) != getattr(after, field)
           for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
        raise ValueError('Bench input changed while being read')
    session = json.loads(body)
    if not isinstance(session, dict):
        raise ValueError('Bench export must be an object')
    return session


def delta(current, reference):
    return [round((a - b + 180) % 360 - 180, 4) for a, b in zip(current, reference)]


def analyze_session(session, reference_quality='unknown'):
    if reference_quality not in ('unknown', 'estimated', 'measured'):
        raise ValueError('Reference must be unknown, estimated or measured')
    markers = session.get('markers')
    if not isinstance(markers, list) or not 1 <= len(markers) <= 200:
        raise ValueError('Expected 1–200 bench markers')
    for marker in markers:
        for channel in ('aircraft', 'gimbal'):
            angles = marker.get(channel)
            if not finite_vector(angles, 3):
                raise ValueError('Invalid bench angle array')
        if marker.get('mode') != 'live':
            raise ValueError('Physical bench analysis requires live-mode annotations')
    starts = [i for i, m in enumerate(markers) if m.get('label') == 'Stationary baseline']
    if not starts:
        raise ValueError('No stationary baseline recorded')
    start = starts[-1]
    baseline = markers[start]
    rows, returns = [], []
    pending = None
    cycle_axes = []
    for marker in markers[start + 1:]:
        axis = marker.get('expected_axis')
        if axis in ('yaw', 'pitch', 'roll'):
            change = delta(marker['aircraft'], baseline['aircraft'])
            dominant = max(range(3), key=lambda i: abs(change[i]))
            magnitude = abs(change[dominant])
            cross = max(abs(change[i]) for i in range(3) if i != dominant)
            requested = marker.get('expected_degrees')
            normalized = (change[dominant] * (1 if requested > 0 else -1)
                          if type(requested) in (int, float) and requested != 0 else 0)
            row = {'physical_action': axis, 'marker_label': marker['label'],
                   'baseline_label': baseline['label'], 'aircraft_delta_deg': change,
                   'gimbal_delta_deg': delta(marker['gimbal'], baseline['gimbal']),
                   'dominant_field': 'ABC'[dominant], 'dominant_delta_deg': change[dominant],
                   'sign_for_positive_operator_action': 'positive' if normalized > 0 else 'negative' if normalized < 0 else 'undetermined',
                   'cross_axis_max_deg': cross,
                   'cross_axis_fraction': round(cross / magnitude, 4) if magnitude else None,
                   'requested_angle_deg': marker.get('expected_degrees'),
                   'angle_reference': reference_quality,
                   'scale_validated': False,
                   'scale_status': 'requires_measured_reference' if reference_quality != 'measured' else 'requires_repeated_measured_comparisons',
                   'aircraft_sample_count': marker.get('aircraft_sample', {}).get('sample_count'),
                   'gimbal_sample_count': marker.get('gimbal_sample', {}).get('sample_count')}
            rows.append(row)
            pending = (axis, dominant, baseline)
            cycle_axes.append(axis)
        elif axis in ('baseline', 'end'):
            if pending:
                physical_axis, field, prior_baseline = pending
                changes = delta(marker['aircraft'], prior_baseline['aircraft'])
                returns.append({'after_action': physical_axis, 'marker_label': marker['label'],
                                'aircraft_return_error_deg': changes,
                                'gimbal_return_error_deg': delta(marker['gimbal'], prior_baseline['gimbal']),
                                'dominant_field_return_error_deg': changes[field],
                                'dominant_field_within_provisional_3_deg': abs(changes[field]) <= 3,
                                'all_fields_within_provisional_3_deg': max(abs(x) for x in changes) <= 3})
                pending = None
            baseline = marker
    candidate = {row['dominant_field']: {'physical_axis': row['physical_action'],
                 'positive_direction': row['sign_for_positive_operator_action']} for row in rows}
    low_samples = [m['label'] for m in markers[start:] if
                   (m.get('aircraft_sample', {}).get('sample_count') or 0) < 3]
    pair_summaries = [{'marker_label': marker.get('label'), **summarize_exported_gimbal_pairs(marker)}
                      for marker in markers[start:]]
    return {'schema': 'neo2.bench-analysis.v1', 'session_id': session.get('session_id'),
            'recorded_markers': len(markers), 'analyzed_start_index': start,
            'duplicate_or_earlier_baselines': len(starts) - 1,
            'complete_first_cycle': cycle_axes == ['yaw', 'pitch', 'roll'] and bool(returns) and markers[-1].get('expected_axis') == 'end',
            'physical_angle_reference': reference_quality,
            'movements': rows, 'returns': returns,
            'candidate_axis_mapping': candidate,
            'distinct_dominant_fields': len(candidate) == len(rows) == 3,
            'final_vs_start_aircraft_deg': delta(markers[-1]['aircraft'], markers[start]['aircraft']),
            'final_vs_start_gimbal_deg': delta(markers[-1]['gimbal'], markers[start]['gimbal']),
            'physical_calibration_verified': False,
            'repeatability_established': False,
            'gimbal_paired_evidence': {'markers': pair_summaries,
                'retained_pairs_total': sum(row['retained_pairs'] for row in pair_summaries),
                'quaternion_convention_verified': False,
                'scope': 'Structural same-packet evidence inventory; no quaternion fit or physical calibration'},
            'sample_quality': {'marks_with_fewer_than_3_aircraft_samples': low_samples,
                               'limits': 'Single-sample zero spread does not establish stationary stability.'},
            'next_test': 'Repeat each direction three times with a measured angle reference, fixed heading for tilts, and a longer steady sample window.',
            'drone_commands_sent_by_analysis': 0}
