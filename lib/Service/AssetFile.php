<?php

declare(strict_types=1);

namespace OCA\CadviewerNextcloud\Service;

/** Read only shipped static assets. This must never serve conversion outputs. */
final class AssetFile {
    private const TYPES = [
        'css' => 'text/css; charset=UTF-8',
        'js' => 'text/javascript; charset=UTF-8',
        'xml' => 'application/xml; charset=UTF-8',
        'png' => 'image/png', 'svg' => 'image/svg+xml',
        'jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg',
        'gif' => 'image/gif', 'bmp' => 'image/bmp', 'ico' => 'image/x-icon',
        'ttf' => 'font/ttf', 'otf' => 'font/otf',
        'woff' => 'font/woff', 'woff2' => 'font/woff2',
        'eot' => 'application/vnd.ms-fontobject',
    ];
    private const MAX_BYTES = 8 * 1024 * 1024;

    /** @return array{content: string, type: string}|null */
    public function read(string $path): ?array {
        // The router has already decoded the URL. Do not decode it again.
        if ($path === '' || strlen($path) > 1024 ||
            preg_match('/[\x00-\x1f\x7f\\\\:%]/', $path)) {
            return null;
        }
        $parts = explode('/', $path);
        foreach ($parts as $part) {
            if ($part === '' || $part[0] === '.') {
                return null;
            }
        }
        $type = self::TYPES[strtolower(pathinfo($path, PATHINFO_EXTENSION))] ?? null;
        if ($type === null) {
            return null;
        }
        $root = realpath(__DIR__ . '/../../assets');
        if ($root === false) {
            return null;
        }
        $file = $root;
        foreach ($parts as $part) {
            $file .= '/' . $part;
            if (is_link($file)) {
                return null;
            }
        }
        $canonical = realpath($file);
        if ($canonical === false || !str_starts_with($canonical, $root . '/') ||
            !is_file($canonical) || !is_readable($canonical)) {
            return null;
        }
        // Assets belong to the read-only app package. Bound the read even if an
        // invalid package contains an unexpectedly large regular file.
        $content = file_get_contents($canonical, false, null, 0, self::MAX_BYTES + 1);
        if ($content === false || strlen($content) > self::MAX_BYTES) {
            return null;
        }
        return ['content' => $content, 'type' => $type];
    }
}
