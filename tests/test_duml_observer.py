import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.duml_observer import Stream, crc8, crc16

# Published offline vector from smichea/dji-neo2-lan-client/tests/test_duml.py.
# It is framing evidence only and is never transmitted by this repository.
VECTOR = bytes.fromhex('551104922a283412400409deadbeef35e6')


class DumlObserverTests(unittest.TestCase):
    def test_published_vector(self):
        frame, = Stream().feed(VECTOR)
        self.assertEqual((frame.sender, frame.receiver, frame.sequence), (0x2a, 0x28, 0x1234))
        self.assertEqual(frame.command, (4, 9))
        self.assertEqual(crc8(VECTOR[:3]), 0x92)
        self.assertEqual(crc16(VECTOR[:-2]), 0xe635)

    def test_every_usb_split_point(self):
        for split in range(len(VECTOR) + 1):
            stream = Stream()
            frames = stream.feed(VECTOR[:split]) + stream.feed(VECTOR[split:])
            self.assertEqual([f.raw for f in frames], [VECTOR])

    def test_corrupt_bytes_rejected_and_following_frame_recovers(self):
        for index in range(len(VECTOR)):
            bad = bytearray(VECTOR)
            bad[index] ^= 0x80
            frames = Stream().feed(bytes(bad) + VECTOR)
            self.assertEqual([f.raw for f in frames], [VECTOR])

    def test_noise_and_multiple_frames(self):
        stream = Stream()
        self.assertEqual(len(stream.feed(b'\x00\xaa' + VECTOR * 2)), 2)
        self.assertEqual(stream.discarded, 2)

    def test_empty_has_no_protocol_evidence(self):
        self.assertEqual(Stream().feed(b''), [])


if __name__ == '__main__':
    unittest.main()
