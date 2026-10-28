"""Public distribution tests; standard library only, no private fonts or network."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


fonts = module('prepare-bundled-fonts')
package = module('package-app')
worker = module('init-worker')


class DistributionTests(unittest.TestCase):
    def test_all_public_fonts_keep_notices_and_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'stage'
            previous = os.umask(0o077)
            try:
                contents = fonts.stage(ROOT / 'fonts', target)
            finally:
                os.umask(previous)
            self.assertEqual(len(list((target / 'fonts').glob('*.ttf'))), 10)
            self.assertIn('licenses/vazirmatn/OFL.txt', contents)
            self.assertIn('licenses/liberation/LICENSE', contents)
            for name, data in contents.items():
                self.assertEqual((target / name).read_bytes(), data)
                self.assertEqual(stat.S_IMODE((target / name).stat().st_mode), 0o644)
                self.assertEqual(stat.S_IMODE((target / name).parent.stat().st_mode), 0o755)
            with self.assertRaises(ValueError):
                fonts.stage(ROOT / 'fonts', target)

    def test_tampered_input_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            shutil.copytree(ROOT / 'fonts', source)
            (source / 'liberation/LICENSE').write_text('changed notice')
            output = Path(temp) / 'output'
            with self.assertRaises(ValueError):
                fonts.stage(source, output)
            self.assertFalse(output.exists())

    def test_unsafe_manifest_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            shutil.copytree(ROOT / 'fonts', source)
            notice = source / 'liberation/LICENSE'
            notice.unlink()
            notice.symlink_to(ROOT / 'fonts/liberation/LICENSE')
            with self.assertRaises(ValueError):
                fonts.verified_files(source)
            manifest = json.loads((source / 'manifest.json').read_text())
            manifest['families'][0]['files'][0]['path'] = '../outside.ttf'
            (source / 'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                fonts.verified_files(source)

    def test_worker_secret_and_paths_and_existing_deployment(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'worker'
            worker.initialize(target, 'a' * 64, '127.0.0.1', 8090, ROOT)
            before = (target / 'worker-token').read_bytes()
            self.assertRegex(before.decode().strip(), r'^[A-Za-z0-9_-]{64}$')
            self.assertEqual(stat.S_IMODE((target / 'worker-token').stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((target / 'fonts').stat().st_mode), 0o755)
            config = json.loads((target / 'config.json').read_text())
            self.assertEqual(config['fonts'], str(target / 'fonts'))
            self.assertTrue(Path(config['scratch']).is_dir())
            with self.assertRaises(ValueError):
                worker.initialize(target, 'b' * 64, '127.0.0.1', 8090, ROOT)
            self.assertEqual((target / 'worker-token').read_bytes(), before)

    def test_invalid_worker_parameters_do_not_create_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'worker'
            for image, bind, port in [('latest', '127.0.0.1', 8090), ('a' * 64, '0.0.0.0', 8090),
                                      ('a' * 64, '8.8.8.8', 8090), ('a' * 64, '127.0.0.1', 80)]:
                with self.assertRaises(ValueError):
                    worker.initialize(target, image, bind, port, ROOT)
                self.assertFalse(target.exists())

    def test_app_package_is_deterministic_and_excludes_private_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'
            root.mkdir()
            for name, data in [('appinfo/info.xml', '<info><version>1.2.3</version></info>'),
                               ('js/cadviewer-files.js', 'built'), ('assets/viewer/frame.js', 'frame'),
                               ('COPYING', 'license'), ('src/files.js', 'source'),
                               ('worker/token', 'secret'), ('.local/private.dwg', 'private'),
                               ('fonts/secret.shx', 'private font'), ('node_modules/a.js', 'dependency')]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(data)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            a, _ = package.package(root, Path(temp) / 'a')
            b, _ = package.package(root, Path(temp) / 'b')
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with tarfile.open(a) as archive:
                names = archive.getnames()
                self.assertEqual(len(names), 5)
                self.assertIn('cadviewer_nextcloud/src/files.js', names)
                self.assertTrue(all(m.isfile() and m.uid == m.gid == m.mtime == 0 for m in archive))
            (root / 'src/files.js').unlink()
            (root / 'src/files.js').symlink_to(root / 'worker/token')
            with self.assertRaises(ValueError):
                package.package(root, Path(temp) / 'c')


if __name__ == '__main__':
    unittest.main()
