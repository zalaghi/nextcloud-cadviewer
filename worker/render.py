#!/usr/bin/env python3
"""Offline, open-source CAD rendering. Run only in the bounded parser container.

SPDX-License-Identifier: AGPL-3.0-or-later
LibreDWG and ezdxf retain their own GPL-3.0-or-later and MIT licenses.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, layout, svg
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, ImagePolicy, LineweightPolicy
from ezdxf.fonts import fonts
from ezdxf.math import Vec3

NASKHD_SHA256 = '2252d08c0d5bc27e5e636dc72529946c0dc8fe8fc5281ba91db2e22839d4696d'
MAX_INPUT = 32 * 1024 * 1024
MAX_SVG = 16 * 1024 * 1024


def legacy_naskhd_glyphs(text):
    """Recover SHX byte glyph indices only for the fingerprinted legacy font.

    KATEB TEXT is already ordered and positioned in the drawing. Do not reverse,
    reshape, translate or apply a Unicode bidi algorithm to those glyphs.
    """
    result = []
    for character in text:
        if ord(character) > 255:
            # Legacy files contain both Windows Arabic and Western byte decodings.
            # These code pages agree on the shared punctuation; try Arabic first.
            for encoding in ('cp1256', 'cp1252'):
                try:
                    encoded = character.encode(encoding)
                    if len(encoded) == 1:
                        character = chr(encoded[0])
                        break
                except UnicodeEncodeError:
                    pass
        result.append(character)
    return ''.join(result)


def prepare_fonts(doc, directory):
    fonts.font_manager.build(folders=[str(directory), '/usr/share/fonts'], support_dirs=False)
    by_name = {p.name.casefold(): p for p in directory.iterdir() if p.is_file() and not p.is_symlink()}
    known_font = by_name.get('naskhd.shx')
    legacy_available = bool(known_font and hashlib.sha256(known_font.read_bytes()).hexdigest() == NASKHD_SHA256)
    legacy_styles, missing = set(), set()
    for style in doc.styles:
        # Font references can never become arbitrary server-side paths.
        name = style.dxf.font.replace('\\', '/').split('/')[-1]
        style.dxf.font = name
        style.dxf.bigfont = style.dxf.bigfont.replace('\\', '/').split('/')[-1]
        if name and not fonts.font_manager.has_font(name):
            missing.add(name[:100])
        if legacy_available and name.casefold() == 'naskhd.shx':
            legacy_styles.add(style.dxf.name.casefold())
    changed = 0
    for entity in doc.entitydb.values():
        if entity is None or not entity.is_alive:
            continue
        if entity.dxftype() not in ('TEXT', 'ATTRIB', 'ATTDEF', 'MTEXT'):
            continue
        if entity.dxf.get('style', 'Standard').casefold() not in legacy_styles:
            continue
        original = entity.text if entity.dxftype() == 'MTEXT' else entity.dxf.text
        if entity.dxftype() == 'MTEXT' and '\\f' in original.lower():
            continue  # Mixed inline fonts need a separate, explicit interpretation.
        mapped = legacy_naskhd_glyphs(original)
        if mapped != original:
            changed += 1
            if entity.dxftype() == 'MTEXT':
                entity.text = mapped
            else:
                entity.dxf.text = mapped
    return sorted(missing), changed


class LayeredRenderBackend(svg.SVGRenderBackend):
    def mark(self, before, properties):
        if len(self.entities) > 200000:
            raise ValueError('Drawing exceeds geometry limit')
        if len(self.entities) > before:
            self.entities[-1].set('data-layer', properties.layer[:255])
            self.entities[-1].set('data-entity', properties.handle[:32])

    def add_strokes(self, d, properties):
        before = len(self.entities)
        super().add_strokes(d, properties)
        self.mark(before, properties)

    def add_filling(self, d, properties):
        before = len(self.entities)
        super().add_filling(d, properties)
        self.mark(before, properties)


class LayeredSVGBackend(svg.SVGBackend):
    @staticmethod
    def make_backend(page, settings):
        return LayeredRenderBackend(page, settings)


def render(drawing, font_directory, layout_index=0, dwg2dxf='/usr/local/bin/dwg2dxf'):
    if not drawing.is_file() or drawing.stat().st_size > MAX_INPUT:
        raise ValueError('Drawing exceeds input limit')
    if drawing.suffix.lower() == '.dwg':
        converted = Path('/scratch/drawing.dxf')
        # No shell, network, user-selected flags, or access to other drawings.
        subprocess.run([dwg2dxf, '-v0', '-y', '-o', str(converted), str(drawing)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        if converted.stat().st_size > 128 * 1024 * 1024:
            raise ValueError('Intermediate drawing exceeds size limit')
        source = converted
    elif drawing.suffix.lower() == '.dxf':
        source = drawing
    else:
        raise ValueError('Only DWG and DXF are supported')
    doc = ezdxf.readfile(source)
    if len(doc.entitydb) > 200000:
        raise ValueError('Drawing exceeds entity limit')
    if len(doc.layers) > 2000:
        raise ValueError('Drawing exceeds layer limit')
    names = doc.layout_names_in_taborder()[:32]
    if not 0 <= layout_index < len(names):
        raise ValueError('Layout does not exist')
    missing, mapped = prepare_fonts(doc, font_directory)
    selected = doc.layouts.get(names[layout_index])
    context = RenderContext(doc)
    backend = LayeredSVGBackend()
    configuration = Configuration(background_policy=BackgroundPolicy.WHITE,
        color_policy=ColorPolicy.COLOR, image_policy=ImagePolicy.IGNORE,
        lineweight_policy=LineweightPolicy.RELATIVE)
    Frontend(context, backend, config=configuration).draw_layout(selected, finalize=True)
    root = backend.get_xml_root_element(layout.Page(0, 0), settings=layout.Settings(max_stroke_width=0.002, min_stroke_width=0.1))
    if root.get('viewBox') is None:
        raise ValueError('The selected layout contains no visible geometry')
    root.set('id', 'cad-drawing')
    layers = sorted({node.get('data-layer') for node in root.iter() if node.get('data-layer') is not None})
    scale = backend.transformation_matrix.transform_direction(Vec3(1, 0, 0)).magnitude
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid drawing scale')
    unit_names = {0: 'drawing units', 1: 'in', 2: 'ft', 4: 'mm', 5: 'cm', 6: 'm', 7: 'km', 14: 'dm'}
    info = {'layouts': names, 'layout': layout_index, 'layers': layers,
            'unitsPerSvgUnit': 1 / scale,
            'unit': unit_names.get(doc.units, 'drawing units') if layout_index == 0 else 'layout units',
            'missingFonts': missing, 'legacyTextEntities': mapped,
            'renderer': 'ezdxf ' + ezdxf.__version__}
    ET.SubElement(root, 'metadata', id='cadviewer-info').text = json.dumps(info, ensure_ascii=False, allow_nan=False)
    result = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    if len(result) > MAX_SVG:
        raise ValueError('Drawing preview exceeds output limit')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('drawing', type=Path)
    parser.add_argument('--fonts', type=Path, default=Path('/fonts'))
    parser.add_argument('--layout', type=int, default=0)
    args = parser.parse_args()
    sys.stdout.buffer.write(render(args.drawing, args.fonts, args.layout))


if __name__ == '__main__':
    main()
