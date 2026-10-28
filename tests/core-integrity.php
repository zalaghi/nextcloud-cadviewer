<?php
declare(strict_types=1);
if (getcwd() !== '/scratch/nextcloud') { throw new RuntimeException('Disposable lab only'); }
$manifest = [];
foreach (['core', 'lib', 'config'] as $directory) {
    foreach (new RecursiveIteratorIterator(new RecursiveDirectoryIterator($directory, FilesystemIterator::SKIP_DOTS)) as $file) {
        if ($file->isFile()) { $manifest[$file->getPathname()] = hash_file('sha256', $file->getPathname()); }
    }
}
$manifest['.htaccess'] = hash_file('sha256', '.htaccess');
ksort($manifest);
$encoded = json_encode($manifest, JSON_THROW_ON_ERROR);
require 'config/config.php';
$configHashes = array_map(static fn ($v) => hash('sha256', serialize($v)), $CONFIG);
if (($argv[1] ?? '') === 'before') { file_put_contents('/scratch/config-values.json', json_encode($configHashes)); }
if (($argv[1] ?? '') === 'before') { file_put_contents('/scratch/core-manifest.json', $encoded); }
elseif (file_get_contents('/scratch/core-manifest.json') !== $encoded) {
    $before = json_decode(file_get_contents('/scratch/core-manifest.json'), true, 512, JSON_THROW_ON_ERROR);
    foreach (array_unique(array_merge(array_keys($before), array_keys($manifest))) as $path) {
        if (($before[$path] ?? null) !== ($manifest[$path] ?? null)) { fwrite(STDERR, 'Changed path: ' . $path . "\n"); }
    }
    $oldConfig = json_decode(file_get_contents('/scratch/config-values.json'), true);
    foreach (array_unique(array_merge(array_keys($oldConfig), array_keys($configHashes))) as $key) {
        if (($oldConfig[$key] ?? null) !== ($configHashes[$key] ?? null)) { fwrite(STDERR, 'Changed config key: ' . $key . "\n"); }
    }
    fwrite(STDERR, "FAIL core/config/.htaccess changed\n"); exit(1);
}
else { echo 'PASS core, lib, config and .htaccess unchanged (' . count($manifest) . " files)\n"; }
