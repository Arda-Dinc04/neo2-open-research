#!/usr/bin/env python3
"""Analyze a saved bench session; no device access or packet transmission."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.bench_analysis import analyze_session, read_bench_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--reference', choices=('unknown', 'estimated', 'measured'), default='unknown')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        result = analyze_session(read_bench_session(args.session), args.reference)
    except (OSError, ValueError, TypeError):
        parser.exit(2, 'Could not analyze the regular bench export within the 64 MiB bound.\n')
    try:
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except OSError:
        parser.exit(2, 'Could not create a new private analysis file; check the output path.\n')
    with os.fdopen(fd, 'w') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'complete_cycle': result['complete_first_cycle'],
                      'candidate_axis_mapping': result['candidate_axis_mapping'],
                      'physical_calibration_verified': False}, indent=2))


if __name__ == '__main__':
    main()
