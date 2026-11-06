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
    return {'attitude_tenths_raw': list(struct.unpack_from('<hhh', payload, 24)),
            'attitude_degrees_sdk_order': [v / 10 for v in struct.unpack_from('<hhh', payload, 24)],
            'relative_height_raw': struct.unpack_from('<h', payload, 16)[0],
            'relative_height_m_sdk_interpretation': struct.unpack_from('<h', payload, 16)[0] / 10,
            'velocity_raw': list(struct.unpack_from('<hhh', payload, 18)),
            'physical_units_and_axes_verified': False}


def component_summary(observations):
    observations = list(observations)
    gimbals, controllers = [], []
    commands = Counter()
    rejected = Counter()
    for observation in observations:
        for frame in observation['frames']:
            commands[f'{frame.command[0]:02x}/{frame.command[1]:02x}'] += 1
            try:
                if frame.sender == 4 and frame.command == (4, 5) and frame.raw[8] & 7 == 0:
                    gimbals.append(gimbal_fields(frame.payload))
                if frame.sender == 3 and frame.command == (3, 0x43) and frame.raw[8] & 7 == 0:
                    controllers.append(fc_fields(frame.payload))
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
                    'reason': 'No validated battery decoder for these captured streams'},
        'rejected_layouts': dict(rejected),
        'interpretation_limits': ['SDK field mapping is not physical calibration.',
                                  'No camera/body alignment or capture-clock synchronization established.',
                                  'No physical chip ownership or transceiver endpoint inferred from host IDs.'],
    }
