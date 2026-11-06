#!/usr/bin/env python3
"""Profile saved DUML traffic without exporting payload bytes or opening USB."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.packet_profiles import profile_observations
from transport.routing_audit import read_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = profile_observations(observation for capture in args.captures
                                  for observation in read_capture(capture))
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(f"Profiled {sum(s['frame_count'] for s in report['segments'])} frames; no payload values exported.")


if __name__ == '__main__':
    main()
