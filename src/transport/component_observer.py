"""Source-backed, provisional field inspection of already-captured packets.

No hardware I/O. Numeric field interpretations are not a calibration or a
flight-ready sensor API. Geographic location is deliberately not exported.
"""
from collections import Counter
import math
import struct


def gimbal_fields(payload):
    if len(payload) != 50:
        raise ValueError('Expected the observed 50-byte gimbal layout')
    raw_angles = struct.unpack_from('<hhh', payload, 0)
    quaternion = struct.unpack_from('<ffff', payload, 24)
    if not all(math.isfinite(v) for v in quaternion):
        raise ValueError('Nonfinite gimbal quaternion fields')
    return {'angles_tenths_raw': list(raw_angles),
            'angles_degrees_sdk_order': [v / 10 for v in raw_angles],
            'quaternion_fields_sdk_order': list(quaternion),
            'quaternion_norm': math.sqrt(sum(v * v for v in quaternion)),
            'field_mapping': 'pitch, roll, yaw per referenced SDK reconstruction',
            'physical_reference_frame_verified': False}


def fc_fields(payload):
    if len(payload) != 85:
        raise ValueError('Expected the locally observed 85-byte FC OSD layout')
    flags = struct.unpack_from('<I', payload, 32)[0]
    return {'attitude_tenths_raw': list(struct.unpack_from('<hhh', payload, 24)),
            'attitude_degrees_sdk_order': [v / 10 for v in struct.unpack_from('<hhh', payload, 24)],
            'relative_height_raw': struct.unpack_from('<h', payload, 16)[0],
            'relative_height_m_sdk_interpretation': struct.unpack_from('<h', payload, 16)[0] / 10,
            'velocity_raw': list(struct.unpack_from('<hhh', payload, 18)),
            'sdk_status_candidates': {'controller_flags_raw': flags,
                                      'mode_code': payload[30] & 0x7f,
                                      'motors_on_bit': bool(flags & 8),
                                      'flying_pattern': flags & 0x0e == 0x0c,
                                      'physical_state_semantics_verified': False},
            'physical_units_and_axes_verified': False}


def component_summary(observations):
    observations = list(observations)
    gimbals, controllers = [], []
    commands = Counter()
    rejected = Counter()
    legacy_battery_values = []
    orientation_flags_rejected = 0
    for observation in observations:
        for frame in observation['frames']:
            commands[f'{frame.command[0]:02x}/{frame.command[1]:02x}'] += 1
            flags = frame.raw[8]
            aircraft = frame.sender == 3 and frame.command == (3, 0x43)
            gimbal = frame.sender == 4 and frame.command == (4, 5)
            if (aircraft and flags not in (0, 0x20, 0x40)) or (gimbal and flags != 0):
                orientation_flags_rejected += 1
                continue
            try:
                if gimbal:
                    gimbals.append(gimbal_fields(frame.payload))
                if aircraft:
                    controllers.append(fc_fields(frame.payload))
                    legacy_battery_values.append(frame.payload[40])
            except ValueError:
                rejected[f'{frame.command[0]:02x}/{frame.command[1]:02x}'] += 1
    def ranges(values, key):
        if not values:
            return None
        columns = list(zip(*(v[key] for v in values)))
        return [{'min': min(col), 'max': max(col)} for col in columns]
    return {
        'scope': 'offline provisional decoder; no new commands; location bytes excluded',
        'physically_calibrated': False,
        'command_counts': dict(sorted(commands.items())),
        'gimbal': {'frames': len(gimbals),
                   'first': gimbals[0] if gimbals else None,
                   'angles_degrees_sdk_order_ranges': ranges(gimbals, 'angles_degrees_sdk_order'),
                   'quaternion_norm_range': {'min': min(g['quaternion_norm'] for g in gimbals),
                                              'max': max(g['quaternion_norm'] for g in gimbals)} if gimbals else None},
        'flight_controller_osd': {'frames': len(controllers),
                                  'first': controllers[0] if controllers else None,
                                  'attitude_degrees_sdk_order_ranges': ranges(controllers, 'attitude_degrees_sdk_order')},
        'battery': {'dedicated_03_55_frames': commands.get('03/55', 0),
                    'percentage_available': False,
                    'reason': 'No validated battery decoder for these captured streams',
                    'legacy_osd_byte_40_hypothesis': {
                        'sample_count': len(legacy_battery_values),
                        'min': min(legacy_battery_values) if legacy_battery_values else None,
                        'max': max(legacy_battery_values) if legacy_battery_values else None,
                        'outside_percent_range': sum(v > 100 for v in legacy_battery_values),
                        'mapping_contradicted_by_range': any(v > 100 for v in legacy_battery_values) if legacy_battery_values else None,
                        'mapping_verified': False,
                        'limit': 'Values within 0–100 alone would not validate the legacy layout.'}},
        'rejected_layouts': dict(rejected),
        'orientation_flags_rejected': orientation_flags_rejected,
        'interpretation_limits': ['SDK field mapping is not physical calibration.',
                                  'No camera/body alignment or capture-clock synchronization established.',
                                  'No physical chip ownership or transceiver endpoint inferred from host IDs.'],
    }
