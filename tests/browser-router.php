<?php
declare(strict_types=1);
// Only used by the disconnected, disposable PHP development server.
if (getcwd() !== '/scratch/nextcloud') { http_response_code(404); exit; }
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
$file = realpath(getcwd() . rawurldecode($path));
if ($file !== false && str_starts_with($file, getcwd() . '/') && is_file($file)
    && in_array(strtolower(pathinfo($file, PATHINFO_EXTENSION)), ['css','js','mjs','png','jpg','svg','gif','ico','woff','woff2','ttf','webp'], true)) { return false; }
if (preg_match('~^/(remote|public|ocs/v[12]|status)\.php(?:/|$)~', $path, $match)) {
    require getcwd() . '/' . $match[1] . '.php';
    return;
}
require getcwd() . '/index.php';
