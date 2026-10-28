import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('fonts', Path(__file__).parents[1] / 'scripts/prepare-persian-fonts.py')
fonts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fonts)


class FontPreparationTests(unittest.TestCase):
    def test_misnamed_truetype_is_staged_by_actual_format(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'; source.mkdir()
            data = b'\x00\x01\x00\x00' + bytes(20)
            (source / 'ARIAL.SHX').write_bytes(data)
            (source / 'script.shx').write_bytes(b'(princ "not a font")')
            (source / 'new.shx').write_bytes(b'AutoCAD-86 shapes 1.1\r\nexample')
            manifest = fonts.inspect_fonts(source, skip_invalid=True)
            target = Path(directory) / 'out'
            previous = os.umask(0o077)
            try:
                fonts.stage_fonts(source, target, manifest)
            finally:
                os.umask(previous)
            self.assertEqual((target / 'arial.ttf').read_bytes(), data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertEqual((target / 'arial.ttf').stat().st_mode & 0o777, 0o644)
            self.assertEqual((target / 'manifest.json').stat().st_mode & 0o777, 0o600)
            self.assertFalse((target / 'ARIAL.SHX').exists())
            self.assertEqual(len(manifest['rejected']), 1)
            self.assertEqual(manifest['font_count'], 2)

    def test_corrected_names_cannot_overwrite_a_different_font(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'arial.shx').write_bytes(b'\x00\x01\x00\x00' + bytes(20))
            (source / 'arial.ttf').write_bytes(b'\x00\x01\x00\x00' + bytes(21))
            with self.assertRaises(ValueError):
                fonts.inspect_fonts(source, skip_invalid=True)

    def test_preserves_bytes_and_bigfont_type_without_loading_lisp(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            data = b'AutoCAD-86 bigfont 1.0\r\n\x1a\x00\x80'
            (source / 'FARS.SHX').write_bytes(data)
            (source / 'KATEB.LSP').write_bytes(b'not a font')
            manifest = fonts.inspect_fonts(source)
            destination = Path(directory) / 'output'
            fonts.stage_fonts(source, destination, manifest)
            self.assertEqual(manifest['font_count'], 1)
            self.assertEqual(manifest['fonts'][0]['kind'], 'bigfont')
            self.assertEqual((destination / 'fars.shx').read_bytes(), data)
            self.assertEqual((destination / 'FARS.SHX').read_bytes(), data)
            self.assertFalse((destination / 'KATEB.LSP').exists())
            with self.assertRaises(ValueError):
                fonts.stage_fonts(source, destination, manifest)

    def test_rejects_case_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'FARSI.SHX').write_bytes(b'AutoCAD-86 shapes 1.0\r\na')
            (source / 'farsi.shx').write_bytes(b'AutoCAD-86 shapes 1.0\r\nb')
            with self.assertRaises(ValueError):
                fonts.inspect_fonts(source)

    def test_rejects_invalid_header_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / 'fake.shx').write_bytes(b'not a font')
            with self.assertRaises(ValueError):
                fonts.inspect_fonts(source)
            (source / 'fake.shx').unlink()
            (source / 'payload').write_bytes(b'AutoCAD-86 shapes 1.0\r\n')
            (source / 'fake.shx').symlink_to(source / 'payload')
            with self.assertRaises(ValueError):
                fonts.inspect_fonts(source)

    def test_rejects_changed_source_before_creating_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            source.mkdir()
            font = source / 'a.shx'
            font.write_bytes(b'AutoCAD-86 shapes 1.0\r\na')
            manifest = fonts.inspect_fonts(source)
            font.write_bytes(b'AutoCAD-86 shapes 1.0\r\nb')
            destination = Path(directory) / 'output'
            with self.assertRaises(ValueError):
                fonts.stage_fonts(source, destination, manifest)
            self.assertFalse(destination.exists())


if __name__ == '__main__':
    unittest.main()
