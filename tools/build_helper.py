#!/usr/bin/env python3
"""Build an observation helper using an existing compiler/libusb installation."""
import argparse
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('usb_stream', 'usb_descriptors'), default='usb_stream')
    args = parser.parse_args()
    compiler = shutil.which('clang') or shutil.which('cc')
    if not compiler:
        raise SystemExit('A C compiler is required; no software was installed.')
    flags = None
    if shutil.which('pkg-config'):
        result = subprocess.run(['pkg-config', '--cflags', '--libs', 'libusb-1.0'], capture_output=True, text=True)
        if result.returncode == 0:
            flags = shlex.split(result.stdout)
    if flags is None:
        for prefix in (Path('/opt/homebrew'), Path('/usr/local'), Path('/usr')):
            if (prefix / 'include/libusb-1.0/libusb.h').exists():
                flags = ['-I' + str(prefix / 'include/libusb-1.0'), '-L' + str(prefix / 'lib'), '-lusb-1.0']
                break
    if flags is None:
        raise SystemExit('libusb development files were not found. Nothing was installed.')
    (ROOT / 'build').mkdir(exist_ok=True)
    source = ROOT / ('native/usb_stream.c' if args.target == 'usb_stream'
                     else 'diagnostics/usb_descriptors.c')
    subprocess.run([compiler, '-Wall', '-Wextra', '-Werror', str(source),
                    *flags, '-o', str(ROOT / 'build' / args.target)], check=True)
    print('Built observation helper: build/' + args.target)


if __name__ == '__main__':
    main()
