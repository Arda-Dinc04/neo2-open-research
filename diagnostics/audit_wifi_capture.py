#!/usr/bin/env python3
"""Audit an existing private camera JSONL capture without opening any device."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from transport.wifi_capture_audit import audit_capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit_capture(args.capture)
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump(report, output, indent=2, allow_nan=False)
            output.write('\n')
    except (OSError, ValueError):
        parser.exit(2, 'Audit failed: check the input format, size and new output path.\n')
    print(f"Audited {report['counts'].get('rx_datagrams', 0)} saved RX datagrams; {len(report['routes'])} header profiles. No device I/O.")


if __name__ == '__main__':
    main()
