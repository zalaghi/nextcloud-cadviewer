<?php
declare(strict_types=1);
if (getcwd() !== '/scratch/nextcloud') { throw new RuntimeException('Disposable lab only'); }
define('OC_CONSOLE', true);
require getcwd() . '/lib/base.php';
set_exception_handler(static function (Throwable $e): void { fwrite(STDERR, $e->getMessage() . "\n"); exit(1); });
$user = \OCP\Server::get(\OCP\IUserManager::class)->get('cadviewer-lab');
\OCP\Server::get(\OCP\IUserSession::class)->setUser($user);
\OCP\Server::get(\OCP\Config\IUserConfig::class)->setValueString('cadviewer-lab', 'firstrunwizard', 'show', '0');
$folder = \OCP\Server::get(\OCP\Files\IRootFolder::class)->getUserFolder('cadviewer-lab');
$folder->newFile('Persian CAD.dxf', file_get_contents('/fixtures/public.dxf'));
$folder->newFile('Persian Plan.dwg', file_get_contents('/fixtures/public.dwg'));
$app = new \OCA\CadviewerNextcloud\AppInfo\Application();
$app->getContainer()->get(\OCA\CadviewerNextcloud\Service\ViewerSettings::class)->save(
    'http://127.0.0.1:8090/convert', str_repeat('d', 48));
echo "Browser fixtures ready\n";
