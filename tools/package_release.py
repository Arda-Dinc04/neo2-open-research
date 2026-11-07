#!/usr/bin/env python3
"""Package a source allowlist, excluding local sessions and raw captures."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('src', 'native', 'viewer', 'diagnostics', 'tests', 'docs', 'tools')
ROOT_FILES = ('README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CONTRIBUTING.md', '.gitignore', 'run_viewer.py', 'AGENTS.md', 'CONTEXT.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT.parent / (ROOT.name + '.zip'))
    args = parser.parse_args()
    destination = args.output.resolve()
    if destination.is_relative_to(ROOT):
        parser.error('Archive must be outside the source directory')
    files = [ROOT / name for name in ROOT_FILES]
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and not path.is_symlink() and not any(
                part in ('__pycache__', 'captures', 'local-data', 'build', '.git')
                for part in path.relative_to(ROOT).parts) and path.suffix not in ('.pyc', '.o', '.so', '.dylib'):
                files.append(path)
    for path in files:
        if not path.exists():
            parser.error('Required source missing: ' + path.name)
        text = path.read_text()
        for private in ('/Users/' + 'ardadinc', '1581FA6QC' + '266801CD6MZ'):
            if private in text:
                parser.error('Private path/device identifier detected: ' + path.name)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
    print(f'Packaged {len(set(files))} source files; excluded sessions and raw captures.')


if __name__ == '__main__':
    main()
