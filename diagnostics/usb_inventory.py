#!/usr/bin/env python3
"""Save cached descriptor inventory or compare saved inventories offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from transport.usb_inventory import collect_inventory, compare_inventories, MODULE_STATES, POWER_STATES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    capture = sub.add_parser('capture', help='Cached descriptors only; no interface claim or device open')
    capture.add_argument('--module-state', choices=MODULE_STATES, default='unknown')
    capture.add_argument('--power-state', choices=POWER_STATES, default='unknown')
    capture.add_argument('--output', type=Path, required=True)
    compare = sub.add_parser('compare', help='Offline; does not access hardware')
    compare.add_argument('before', type=Path)
    compare.add_argument('after', type=Path)
    compare.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new filename')
    if args.action == 'capture':
        report = collect_inventory(ROOT / 'build/usb_descriptors',
                                   module_state=args.module_state, power_state=args.power_state)
    else:
        report = compare_inventories(json.loads(args.before.read_text()), json.loads(args.after.read_text()))
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    if args.action == 'capture':
        print(json.dumps({key: report[key] for key in ('observation_valid', 'observation_status', 'dji_application_bytes_sent')}))
        return 0 if report['observation_valid'] else 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
