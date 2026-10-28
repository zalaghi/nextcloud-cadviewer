#!/usr/bin/env python3
"""Inspect drawing fonts; optionally stage private copies and lowercase aliases.

Never loads AutoLISP, changes drawings, or modifies a live converter directory.
The destination must be absent or empty, so existing fonts cannot be overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path


MAX_FONT_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024


def identify_font(data, name):
    header = data.split(b'\r\n', 1)[0]
    if header in (b'AutoCAD-86 shapes 1.0', b'AutoCAD-86 shapes 1.1',
                  b'AutoCAD-86 bigfont 1.0', b'AutoCAD-86 unifont 1.0'):
        return header.decode('ascii').split()[1], name if Path(name).suffix.lower() == '.shx' else Path(name).stem + '.shx'
    # Some legacy font packs renamed TrueType files to .SHX. Keep their
    # bytes intact and restore the actual format in the private staged copy.
    for signature, kind, suffix in ((b'\x00\x01\x00\x00', 'truetype', '.ttf'),
                                    (b'true', 'truetype', '.ttf'),
                                    (b'OTTO', 'opentype', '.otf'),
                                    (b'ttcf', 'collection', '.ttc')):
        if data.startswith(signature) and len(data) >= 12:
            return kind, Path(name).stem + suffix
    raise ValueError(f'Unrecognized or unsupported font format: {name}')


def inspect_fonts(source, skip_invalid=False):
    source = Path(source).resolve(strict=True)
    records, names, rejected = [], {}, []
    total = 0
    for path in sorted(source.iterdir()):
        if path.suffix.lower() not in ('.shx', '.ttf', '.otf', '.ttc'):
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Expected a regular font file: {path.name}')
        size = path.stat().st_size
        if size > MAX_FONT_BYTES:
            raise ValueError(f'Font exceeds size limit: {path.name}')
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError('Font collection exceeds size limit')
        data = path.read_bytes()
        try:
            kind, staged = identify_font(data, path.name)
        except ValueError:
            if not skip_invalid:
                raise
            rejected.append({'file': path.name, 'reason': 'unrecognized or unsupported font format'})
            continue
        digest = hashlib.sha256(data).hexdigest()
        normalized = staged.casefold()
        if normalized in names and names[normalized] != digest:
            raise ValueError(f'Conflicting case-insensitive font name: {path.name}')
        names[normalized] = digest
        records.append({'file': path.name, 'staged_file': staged, 'lowercase_alias': normalized,
                        'size_bytes': len(data), 'sha256': digest,
                        'kind': kind})
    if not records:
        raise ValueError('No supported font files found')
    by_hash = {}
    for font in records:
        by_hash.setdefault(font['sha256'], []).append(font['file'])
    return {'font_count': len(records), 'unique_contents': len(by_hash),
            'identical_groups': [names for names in by_hash.values() if len(names) > 1],
            'redistribution_license': 'not established; keep supplied fonts private',
            'fonts': records, 'rejected': rejected}


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
        contents[font.get('staged_file', font['file'])] = data
        contents[font['lowercase_alias']] = data
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        with (destination / name).open('xb') as stream:
            stream.write(data)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Folder containing supplied drawing fonts')
    parser.add_argument('--stage', type=Path, help='New private output folder; do not point at a live installation')
    parser.add_argument('--skip-invalid', action='store_true', help='Report and exclude unsupported files; never execute or silently accept them')
    args = parser.parse_args()
    try:
        manifest = inspect_fonts(args.source, skip_invalid=args.skip_invalid)
        if args.stage:
            stage_fonts(args.source, args.stage, manifest)
        print(json.dumps(manifest, indent=2))
    except (ValueError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
