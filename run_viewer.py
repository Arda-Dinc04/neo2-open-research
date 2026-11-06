#!/usr/bin/env python3
"""Run a receive-only local orientation viewer. Default mode is live USB."""
import argparse
import json
from pathlib import Path
import signal
import sys
import threading

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from transport.live_state import LiveState
from transport.live_source import LiveSource, ReplaySource, DemoSource
from viewer_server import ViewerApplication, ViewerServer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('live', 'replay', 'demo'), default='live')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--helper', type=Path, default=ROOT / 'build/usb_stream')
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--session-dir', type=Path, default=ROOT / 'local-data/bench-sessions')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('Port must be between 0 and 65535')
    if args.mode == 'replay' and not args.capture:
        parser.error('Replay mode requires --capture')
    state = LiveState(mode=args.mode)
    if args.mode == 'live':
        source = LiveSource(state, args.helper)
    elif args.mode == 'replay':
        source = ReplaySource(state, args.capture)
    else:
        source = DemoSource(state)
    app = ViewerApplication(state, ROOT / 'viewer', args.session_dir)
    server = ViewerServer(args.port, app)
    def stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        source.start()
        print(json.dumps({'url': f'http://127.0.0.1:{server.server_address[1]}',
                          'mode': args.mode, 'drone_command_api': False}), flush=True)
        server.serve_forever(poll_interval=0.2)
    finally:
        source.stop()
        server.server_close()


if __name__ == '__main__':
    main()
