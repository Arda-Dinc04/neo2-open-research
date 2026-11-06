#!/usr/bin/env python3
"""Analyze a saved bench session; no device access or packet transmission."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.bench_analysis import analyze_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--reference', choices=('unknown', 'estimated', 'measured'), default='unknown')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.session.stat().st_size > 5 * 1024 * 1024:
        parser.error('Session exceeds 5 MiB bound')
    result = analyze_session(json.loads(args.session.read_text()), args.reference)
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'complete_cycle': result['complete_first_cycle'],
                      'candidate_axis_mapping': result['candidate_axis_mapping'],
                      'physical_calibration_verified': False}, indent=2))


if __name__ == '__main__':
    main()
