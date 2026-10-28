#!/usr/bin/env python3
"""Build a deterministic app archive from tracked, allowlisted application files.

Includes the corresponding source and build instructions. Private fonts, tests,
drawings, credentials, worker images and local work directories are excluded.
"""
import argparse
import gzip
import hashlib
import io
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET

DIRECTORIES = {'appinfo', 'assets', 'css', 'img', 'js', 'lib', 'src', 'templates', 'docs'}
FILES = {'COPYING', 'README.md', 'CHANGELOG.md', 'SECURITY.md', 'THIRD_PARTY_NOTICES.md',
         'UPSTREAM.md', 'CONTRIBUTING.md', 'package.json', 'package-lock.json',
         'scripts/build.mjs', 'scripts/build-isolated.sh'}


def app_files(root):
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    selected = []
    for name in sorted(filter(None, tracked)):
        relative = PurePosixPath(name)
        if name not in FILES and relative.parts[0] not in DIRECTORIES:
            continue
        source = root / name
        if (relative.is_absolute() or '..' in relative.parts or not source.is_file()
                or any(p.is_symlink() for p in (source, *source.parents))):
            raise ValueError('Expected a regular tracked application file: ' + name)
        selected.append((name, source.read_bytes(), 0o755 if source.stat().st_mode & 0o111 else 0o644))
    required = {'appinfo/info.xml', 'js/cadviewer-files.js', 'assets/viewer/frame.js', 'COPYING'}
    if not required.issubset(name for name, _, _ in selected):
        raise ValueError('Missing built application files')
    return selected


def package(root, output):
    version = ET.parse(root / 'appinfo/info.xml').findtext('version')
    if not re.fullmatch(r'[0-9A-Za-z.-]+', version or ''):
        raise ValueError('Invalid app version')
    contents = app_files(root)
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'cadviewer_nextcloud-{version}.tar.gz'
    with target.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name, data, mode in contents:
                    entry = tarfile.TarInfo('cadviewer_nextcloud/' + name)
                    entry.size, entry.mode, entry.mtime = len(data), mode, 0
                    entry.uid = entry.gid = 0
                    archive.addfile(entry, io.BytesIO(data))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with Path(str(target) + '.sha256').open('x') as checksum:
        checksum.write(f'{digest}  {target.name}\n')
    return target, len(contents)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.local/releases'))
    args = parser.parse_args()
    try:
        target, count = package(Path(__file__).resolve().parents[1], args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{target} ({count} application/source files; SHA-256 alongside)')


if __name__ == '__main__':
    main()
