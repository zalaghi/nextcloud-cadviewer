"""Run inside the built worker with no private fonts; no network or user drawings."""
import json
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0, '/opt/cadviewer')
import render
import ezdxf
from fontTools.ttLib import TTFont


class BundledFontsTests(unittest.TestCase):
    def test_all_nine_weights_have_persian_glyphs_and_render_without_substitution(self):
        directory = Path('/usr/share/fonts/cadviewer')
        paths = sorted(directory.glob('Vazirmatn-*.ttf'))
        self.assertEqual(len(paths), 9)
        # Coverage and successful outline rendering are deliberately distinct
        # from complex-text shaping or comparison with AutoCAD.
        text = 'سلام فارسی پ چ ژ گ ک ی ۰۱۲۳۴۵۶۷۸۹ 0123456789'
        doc = ezdxf.new()
        for index, path in enumerate(paths):
            with TTFont(path) as font:
                self.assertTrue(set(map(ord, text)).issubset(font.getBestCmap()))
            doc.styles.new(path.stem, dxfattribs={'font': path.name})
            doc.modelspace().add_text(text, dxfattribs={
                'style': path.stem, 'height': 2.5, 'insert': (0, index * 5)})
        fixture = Path('/scratch/vazirmatn.dxf')
        doc.saveas(fixture)
        output = render.render(fixture, Path('/fonts'))
        root = ET.fromstring(output)
        metadata = json.loads(root.find('{http://www.w3.org/2000/svg}metadata').text)
        self.assertEqual(metadata['missingFonts'], [])
        self.assertEqual(metadata['legacyTextEntities'], 0)
        self.assertGreater(len(list(root.iter('{http://www.w3.org/2000/svg}path'))), 0)
        missing, changed = render.prepare_fonts(doc, Path('/fonts'))
        self.assertEqual(changed, 0)
        self.assertTrue(all(entity.dxf.text == text for entity in doc.modelspace()))
        for path in paths:
            self.assertNotIn(path.stem.casefold(), missing)
            self.assertEqual(doc.styles.get(path.stem).dxf.font, path.name)


if __name__ == '__main__':
    unittest.main()
