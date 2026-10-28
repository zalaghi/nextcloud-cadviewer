#!/usr/bin/env python3
"""Inspect SHX files; optionally stage private copies and lowercase aliases.

Never loads AutoLISP, changes drawings, or modifies a live converter directory.
The destination must be absent or empty, so existing fonts cannot be overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path


def inspect_fonts(source):
    source = Path(source).resolve(strict=True)
    records, names = [], {}
    for path in sorted(source.iterdir()):
        if path.suffix.lower() != '.shx':
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Expected a regular font file: {path.name}')
        data = path.read_bytes()
        header = data.split(b'\r\n', 1)[0]
        if header not in (b'AutoCAD-86 shapes 1.0', b'AutoCAD-86 bigfont 1.0', b'AutoCAD-86 unifont 1.0'):
            raise ValueError(f'Unrecognized SHX header: {path.name}')
        digest = hashlib.sha256(data).hexdigest()
        normalized = path.name.lower()
        if normalized in names and names[normalized] != digest:
            raise ValueError(f'Conflicting case-insensitive font name: {path.name}')
        names[normalized] = digest
        records.append({'file': path.name, 'lowercase_alias': normalized,
                        'size_bytes': len(data), 'sha256': digest,
                        'kind': header.decode('ascii').split()[1]})
    if not records:
        raise ValueError('No SHX files found')
    by_hash = {}
    for font in records:
        by_hash.setdefault(font['sha256'], []).append(font['file'])
    return {'font_count': len(records), 'unique_contents': len(by_hash),
            'identical_groups': [names for names in by_hash.values() if len(names) > 1],
            'redistribution_license': 'not established; keep supplied fonts private',
            'fonts': records}


def stage_fonts(source, destination, manifest):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError('Destination must be absent or empty; existing fonts are never overwritten')
    # Verify all inputs before creating any output.
    contents = {}
    for font in manifest['fonts']:
        path = source / font['file']
        if path.is_symlink():
            raise ValueError(f'Input changed after inspection: {path.name}')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != font['sha256']:
            raise ValueError(f'Input changed after inspection: {path.name}')
        contents[font['file']] = data
        contents[font['lowercase_alias']] = data
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Folder containing supplied SHX fonts')
    parser.add_argument('--stage', type=Path, help='New private output folder; do not point at a live installation')
    args = parser.parse_args()
    try:
        manifest = inspect_fonts(args.source)
        if args.stage:
            stage_fonts(args.source, args.stage, manifest)
        print(json.dumps(manifest, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
