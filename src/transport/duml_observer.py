"""Offline DUML v1 recognition. No USB or network transmit functions."""
from dataclasses import dataclass


def checksum(data, initial, polynomial, mask):
    value = initial
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (polynomial if value & 1 else 0)
    return value & mask


def crc8(data):
    return checksum(data, 0x77, 0x8c, 0xff)


def crc16(data):
    return checksum(data, 0x3692, 0x8408, 0xffff)


@dataclass(frozen=True)
class Frame:
    raw: bytes

    @property
    def sender(self):
        return self.raw[4]

    @property
    def receiver(self):
        return self.raw[5]

    @property
    def sequence(self):
        return int.from_bytes(self.raw[6:8], 'little')

    @property
    def command(self):
        return tuple(self.raw[9:11])

    @property
    def payload(self):
        return self.raw[11:-2]


class Stream:
    """Recognize complete frames across USB read boundaries and reject bad CRCs."""
    def __init__(self):
        self.buffer = bytearray()
        self.discarded = 0

    def feed(self, chunk):
        self.buffer.extend(chunk)
        frames = []
        while self.buffer:
            if self.buffer[0] != 0x55:
                del self.buffer[0]
                self.discarded += 1
                continue
            if len(self.buffer) < 4:
                break
            tag = int.from_bytes(self.buffer[1:3], 'little')
            length, version = tag & 0x3ff, tag >> 10
            if version != 1 or not 13 <= length <= 1023 or crc8(self.buffer[:3]) != self.buffer[3]:
                del self.buffer[0]
                self.discarded += 1
                continue
            if len(self.buffer) < length:
                break
            packet = bytes(self.buffer[:length])
            if crc16(packet[:-2]) != int.from_bytes(packet[-2:], 'little'):
                del self.buffer[0]
                self.discarded += 1
                continue
            frames.append(Frame(packet))
            del self.buffer[:length]
        return frames


def analyze_capture(capture):
    result = []
    for observation in capture.get('observations', []):
        stream = Stream()
        frames = []
        for chunk in observation.get('chunks', []):
            frames.extend(stream.feed(bytes.fromhex(chunk['hex'])))
        result.append({
            'interface': observation['interface'],
            'bytes_received': observation.get('bytes_received', 0),
            'crc_valid_frames': len(frames),
            'discarded_bytes': stream.discarded,
            'pending_bytes': len(stream.buffer),
            'observed_peers': sorted({f.sender for f in frames}),
            'frames': [{'sender': f.sender, 'receiver': f.receiver,
                        'sequence': f.sequence, 'command': list(f.command),
                        'payload_hex': f.payload.hex(), 'raw_hex': f.raw.hex()}
                       for f in frames],
        })
    return result
