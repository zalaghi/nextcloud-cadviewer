<?php
declare(strict_types=1);
return ['routes' => [
    ['name' => 'viewer#preview', 'url' => '/api/preview', 'verb' => 'POST'],
    ['name' => 'viewer#frame', 'url' => '/viewer', 'verb' => 'GET'],
    ['name' => 'viewer#asset', 'url' => '/static/{path}', 'verb' => 'GET', 'requirements' => ['path' => '.+']],
    ['name' => 'connection#save', 'url' => '/api/connection', 'verb' => 'POST'],
]];
