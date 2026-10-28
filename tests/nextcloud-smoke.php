<?php
/** Run only in an isolated Nextcloud test installation, from its root directory. */
declare(strict_types=1);
if (getcwd() !== '/scratch/nextcloud') {
    throw new \RuntimeException('Use the disposable lab runner. Never run on an existing installation.');
}

define('OC_CONSOLE', true);
require getcwd() . '/lib/base.php';
set_exception_handler(static function (\Throwable $error): void {
    fwrite(STDERR, get_class($error) . ': ' . $error->getMessage() . PHP_EOL);
    exit(1);
});

$app = new \OCA\CadviewerNextcloud\AppInfo\Application();
$container = $app->getContainer();
$services = [
    \OCA\CadviewerNextcloud\AdminSettings::class,
    \OCA\CadviewerNextcloud\AdminSection::class,
    \OCA\CadviewerNextcloud\Listeners\LoadScriptsListener::class,
    \OCA\CadviewerNextcloud\Controller\ViewerController::class,
    \OCA\CadviewerNextcloud\Controller\ConnectionController::class,
    \OCA\CadviewerNextcloud\Service\DrawingAccess::class,
    \OCA\CadviewerNextcloud\Service\DrawingSvg::class,
];
foreach ($services as $service) {
    $instance = $container->get($service);
    if (!$instance instanceof $service) {
        throw new \RuntimeException('Failed service resolution: ' . $service);
    }
    echo 'PASS resolve ' . $service . PHP_EOL;
}

$response = $container->get(\OCA\CadviewerNextcloud\AdminSettings::class)->getForm();
if (!$response instanceof \OCP\AppFramework\Http\TemplateResponse) {
    throw new \RuntimeException('Admin settings did not return a template');
}
echo 'PASS admin settings template' . PHP_EOL;
echo 'Runtime: Nextcloud ' . implode('.', \OCP\Util::getVersion()) . ', PHP ' . PHP_VERSION . PHP_EOL;
