#!/usr/bin/env python3
"""Build the receive-only helper using an existing compiler/libusb installation."""
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
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
    subprocess.run([compiler, '-Wall', '-Wextra', '-Werror', str(ROOT / 'native/usb_stream.c'),
                    *flags, '-o', str(ROOT / 'build/usb_stream')], check=True)
    print('Built receive-only helper: build/usb_stream')


if __name__ == '__main__':
    main()
