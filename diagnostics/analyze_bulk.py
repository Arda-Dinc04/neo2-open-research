#!/usr/bin/env python3
"""Offline analysis of receive-only USB captures; never accesses hardware."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.duml_observer import analyze_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    capture = json.loads(args.capture.read_text())
    if 'observations' not in capture:
        chunks = [{'hex': capture[key]} for key in
                  ('preflight_rx_hex', 'response_rx_hex') if key in capture]
        capture = {'observations': [{'interface': 4, 'chunks': chunks,
                    'bytes_received': sum(len(bytes.fromhex(c['hex'])) for c in chunks)}]}
    analysis = analyze_capture(capture)
    if args.output:
        with args.output.open('x') as handle:
            json.dump(analysis, handle, indent=2)
            handle.write('\n')
    for interface in analysis:
        print(json.dumps({k: v for k, v in interface.items() if k != 'frames'}))


if __name__ == '__main__':
    main()
