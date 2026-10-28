<?php
declare(strict_types=1);
// Integration fixture: previously converted real CAD output, not a production worker.
if (getcwd() !== '/scratch/nextcloud' || ($_SERVER['HTTP_AUTHORIZATION'] ?? '') !== 'Bearer ' . str_repeat('d', 48)) {
    http_response_code(401); exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || $_SERVER['REQUEST_URI'] !== '/convert') { http_response_code(404); exit; }
header('Content-Type: image/svg+xml');
header('Cache-Control: no-store');
if (($_SERVER['HTTP_X_CAD_LAYOUT'] ?? '0') !== '0') { http_response_code(422); exit; }
readfile(($_SERVER['HTTP_X_CAD_FORMAT'] ?? '') === 'dwg' ? '/fixtures/dwg.svg' : '/fixtures/public.svg');
