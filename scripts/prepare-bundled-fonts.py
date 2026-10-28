#!/usr/bin/env python3
"""Verify the public font manifest; optionally stage fonts and their notices."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def verified_files(root):
    root = Path(root)
    manifest = json.loads((root / 'manifest.json').read_text())
    if manifest['schema_version'] != 1:
        raise ValueError('Unsupported font manifest')
    outputs, names = {}, set()
    for family in manifest['families']:
        if not re.fullmatch(r'[a-z0-9-]+', family['id']):
            raise ValueError('Invalid font family identifier')
        if family['license'] != 'OFL-1.1' or not any(f['kind'] == 'notice' for f in family['files']):
            raise ValueError('A bundled font family needs its redistribution notice')
        for item in family['files']:
            relative = PurePosixPath(item['path'])
            if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                raise ValueError('Unsafe manifest path')
            source = root.joinpath(*relative.parts)
            if any(p.is_symlink() for p in (source, *source.parents)) or not source.is_file():
                raise ValueError('Expected a regular font or notice file')
            data = source.read_bytes()
            if len(data) != item['size_bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
                raise ValueError(f'Bundled font checksum mismatch: {relative}')
            if item['kind'] == 'font':
                if len(data) > 16 * 1024 * 1024 or not data.startswith(b'\x00\x01\x00\x00'):
                    raise ValueError('Expected a bounded TrueType font')
                output = 'fonts/' + relative.name
            elif item['kind'] == 'notice':
                output = 'licenses/' + family['id'] + '/' + relative.name
            else:
                raise ValueError('Unknown font manifest entry')
            if output.casefold() in names:
                raise ValueError('Conflicting bundled font output name')
            names.add(output.casefold())
            outputs[output] = data
    outputs['licenses/font-manifest.json'] = (root / 'manifest.json').read_bytes()
    if not any(name.startswith('fonts/') for name in outputs):
        raise ValueError('Empty bundled font manifest')
    return outputs


def stage(root, destination):
    contents = verified_files(root)
    destination = Path(destination).absolute()
    if any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('Destination must not contain symlinks')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Destination must be new or empty')
    for name, data in contents.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        for parent in target.relative_to(destination).parents:
            (destination / parent).chmod(0o755)
        with target.open('xb') as stream:
            stream.write(data)
        target.chmod(0o644)
    return contents


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, help='New or empty staging directory')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / 'fonts'
    try:
        contents = stage(root, args.stage) if args.stage else verified_files(root)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'{error}\n')
    print(f"Verified {sum(name.startswith('fonts/') for name in contents)} bundled fonts and their notices.")


if __name__ == '__main__':
    main()
