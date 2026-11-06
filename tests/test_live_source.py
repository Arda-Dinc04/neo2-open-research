import json
import io
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.live_source import (DemoSource, LiveSource, ReplaySource,
                                   parse_helper_line, replay_chunks, _synthetic_packet)
from transport.live_state import LiveState


class HelperProtocolTests(unittest.TestCase):
    def test_valid_transfer_has_bytes(self):
        parsed = parse_helper_line(json.dumps({'type': 'transfer', 'interface': 4,
                     'endpoint_in': '0x85', 'bytes': 2, 'hex': '550d'}))
        self.assertEqual(parsed['data'], bytes.fromhex('550d'))

    def test_bad_json_endpoint_hex_and_false_readonly_are_rejected(self):
        bad = ['not json', '[]', '{"type":"execute"}',
               '{"type":"ready","interface":3,"endpoint_in":"0x84","read_only":true}',
               '{"type":"ready","interface":4,"endpoint_in":"0x85","read_only":false}',
               '{"type":"transfer","interface":4,"endpoint_in":"0x85","bytes":2,"hex":"ff"}',
               '{"type":"transfer","interface":4,"endpoint_in":"0x85","bytes":1,"hex":"zz"}',
               '{"type":"end","application_bytes_sent":1}']
        for line in bad:
            with self.subTest(line=line), self.assertRaises(ValueError):
                parse_helper_line(line)

    def test_oversized_helper_line_is_bounded(self):
        with self.assertRaises(ValueError):
            parse_helper_line(' ' * 131073)

    def test_missing_helper_reports_error_without_fake_data(self):
        state = LiveState()
        source = LiveSource(state, '/nonexistent/read-only-helper').start()
        source._thread.join(timeout=2)
        self.assertEqual(state.snapshot()['status'], 'error')
        self.assertIsNone(state.snapshot()['aircraft'])

    def test_source_modes_cannot_be_silently_mixed(self):
        with self.assertRaises(ValueError):
            LiveSource(LiveState('demo'), '/tmp/helper')
        with self.assertRaises(ValueError):
            ReplaySource(LiveState('live'), '/tmp/file')
        with self.assertRaises(ValueError):
            DemoSource(LiveState('live'))

    def test_replay_filters_other_interfaces_and_preserves_saved_offsets(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'capture.json'
            path.write_text(json.dumps({'observations': [
                {'interface': 3, 'chunks': [{'hex': 'ffff'}]},
                {'interface': 4, 'chunks': [{'hex': '550d', 'offset_ms': 20}]}]}))
            self.assertEqual(replay_chunks(path), [(20, b'\x55\x0d')])

    def test_empty_replay_is_an_error_not_a_demo(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'capture.json'
            path.write_text('{"observations":[]}')
            state = LiveState('replay')
            source = ReplaySource(state, path, loop=False).start()
            source._thread.join(timeout=2)
            self.assertEqual(state.snapshot()['status'], 'error')
            self.assertIsNone(state.snapshot()['aircraft'])

    def test_demo_is_flagged_and_has_both_channels_without_subprocess(self):
        state = LiveState('demo')
        with patch('transport.live_source.subprocess.Popen') as process:
            source = DemoSource(state).start()
            deadline = time.monotonic() + 1
            while state.snapshot()['gimbal'] is None and time.monotonic() < deadline:
                time.sleep(0.01)
            snapshot = state.snapshot()
            source.stop()
            self.assertEqual(snapshot['mode'], 'demo')
            self.assertIsNotNone(snapshot['aircraft'])
            self.assertIsNotNone(snapshot['gimbal'])
            self.assertIn('Synthetic', snapshot['transport']['source_detail'])
            process.assert_not_called()

    def test_helper_pipeline_has_fixed_arguments_no_stdin_and_no_shell(self):
        raw = _synthetic_packet(3, 10, (3, 0x43), 8, bytes(85))
        lines = [
            {'type': 'ready', 'interface': 4, 'endpoint_in': '0x85', 'read_only': True},
            {'type': 'transfer', 'interface': 4, 'endpoint_in': '0x85',
             'bytes': len(raw), 'hex': raw.hex()},
            {'type': 'end', 'application_bytes_sent': 0, 'exit_code': 0},
        ]
        fake = MagicMock()
        fake.stdout = io.StringIO(''.join(json.dumps(line) + '\n' for line in lines))
        fake.poll.return_value = 0
        state = LiveState('live')
        with patch('transport.live_source.subprocess.Popen', return_value=fake) as launch:
            source = LiveSource(state, '/fixed/path/helper').start()
            source._thread.join(timeout=2)
        args, kwargs = launch.call_args
        self.assertEqual(args[0], ['/fixed/path/helper', '--receive-only'])
        self.assertNotIn('shell', kwargs)
        self.assertEqual(kwargs['stdin'], -3)  # subprocess.DEVNULL
        self.assertEqual(state.snapshot()['transport']['frames_total'], 1)
        self.assertIsNotNone(state.snapshot()['aircraft'])
        self.assertEqual(state.snapshot()['status'], 'disconnected')


if __name__ == '__main__':
    unittest.main()
