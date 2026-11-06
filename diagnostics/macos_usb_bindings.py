#!/usr/bin/env python3
"""Inspect current macOS driver bindings; no device or network probes."""
import argparse
import datetime as dt
import json
from pathlib import Path
import platform
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from transport.macos_bindings import binding_summary


def query(class_name):
    command = ['/usr/sbin/ioreg', '-a', '-r', '-c', class_name, '-l', '-w', '0']
    try:
        process = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                                 timeout=20, check=True)
        return plistlib.loads(process.stdout)
    except (OSError, subprocess.SubprocessError, plistlib.InvalidFileException) as exc:
        raise ValueError('Registry observation failed; no driver-binding conclusion') from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Darwin':
        parser.error('This diagnostic inspects macOS IORegistry only')
    if args.output.exists():
        parser.error('Output exists; choose a new filename')
    report = binding_summary(query('IOUSBHostDevice'), query('IONetworkInterface'))
    report['captured_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['host'] = {'system': platform.system(), 'release': platform.release(), 'machine': platform.machine()}
    with args.output.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({key: report[key] for key in ('observation_valid', 'network_correlation_available', 'devices')}, indent=2))
    return 0 if report['observation_valid'] else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
