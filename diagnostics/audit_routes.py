#!/usr/bin/env python3
"""Audit saved traffic for route aliases and replies; never accesses hardware."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.routing_audit import audit, read_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(o for path in args.captures for o in read_capture(path))
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps({k: report[k] for k in ('total_frames', 'query_search',
                         'possible_session_envelopes', 'encrypted_frames')}, indent=2))


if __name__ == '__main__':
    main()
