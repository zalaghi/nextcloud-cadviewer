<?php
/** Run only in tests/run-nextcloud-lab.sh's disposable installation. */
declare(strict_types=1);
if (getcwd() !== '/scratch/nextcloud') {
    throw new RuntimeException('Use the disposable lab runner. Never run on an existing installation.');
}

define('OC_CONSOLE', true);
require getcwd() . '/lib/base.php';
// Nextcloud's CLI exception handler may exit without a failing process status.
set_exception_handler(static function (Throwable $error): void {
    fwrite(STDERR, get_class($error) . ': ' . $error->getMessage() . PHP_EOL . $error->getTraceAsString() . PHP_EOL);
    exit(1);
});

use OCA\CadviewerNextcloud\Controller\ViewerController;
use OCA\CadviewerNextcloud\Service\PhpRuntime;
use OCA\CadviewerNextcloud\SetupCheck\PhpRuntimeCheck;
use OCP\Server;

function check(bool $ok, string $name): void {
    if (!$ok) {
        throw new RuntimeException('FAIL ' . $name);
    }
    echo 'PASS ' . $name . PHP_EOL;
}

$app = new \OCA\CadviewerNextcloud\AppInfo\Application();
$container = $app->getContainer();
$runtime = $container->get(PhpRuntime::class);
foreach (['8.3.36', '8.4.27', '8.5.12', '8.4.28', '8.5.13'] as $version) {
    check($runtime->meetsBaseline($version), 'patched runtime ' . $version);
}
foreach (['8.2.35', '8.3.35', '8.4.26', '8.5.11', '8.6.0RC4', '8.5.12-RC1', '8.6.0', 'invalid'] as $version) {
    check(!$runtime->meetsBaseline($version), 'reject unqualified runtime ' . $version);
}
check($runtime->meetsBaseline(PHP_VERSION), 'actual test runtime meets baseline');
$setup = $container->get(PhpRuntimeCheck::class);
$expectedSeverity = filter_var(ini_get('session.upload_progress.enabled'), FILTER_VALIDATE_BOOLEAN) ? 'warning' : 'success';
check($setup->run()->getSeverity() === $expectedSeverity, 'session startup setting assessed');

$package = getcwd() . '/custom_apps/cadviewer_nextcloud';
mkdir($package . '/assets/lab-security');
mkdir($package . '/assets-sibling');
file_put_contents($package . '/assets/lab-security/ok.css', '/* trusted fixture */');
file_put_contents($package . '/assets-sibling/secret.svg', 'private-fixture');
file_put_contents($package . '/assets/lab-security/code.php', '<?php echo "not an asset";');
symlink($package . '/assets-sibling/secret.svg', $package . '/assets/lab-security/link.svg');
symlink($package . '/assets-sibling', $package . '/assets/lab-security/link-dir');
$large = fopen($package . '/assets/lab-security/large.png', 'w');
ftruncate($large, 8 * 1024 * 1024 + 1);
fclose($large);
$controller = $container->get(ViewerController::class);
$response = $controller->asset('lab-security/ok.css');
check($response->getStatus() === 200 && $response->render() === '/* trusted fixture */', 'valid asset content');
check($response->getHeaders()['Content-Type'] === 'text/css; charset=UTF-8', 'fixed asset content type');
check($response->getHeaders()['X-Content-Type-Options'] === 'nosniff', 'asset nosniff');
foreach ([
    '../assets-sibling/secret.svg', 'lab-security/../../assets-sibling/secret.svg',
    '/assets-sibling/secret.svg', '%2e%2e/assets-sibling/secret.svg',
    '%252e%252e/assets-sibling/secret.svg', 'lab-security\\..\\secret.svg',
    'file:///etc/passwd', 'https://example.invalid/test.svg',
    "lab-security/ok.css\0.svg", 'lab-security//ok.css',
    'lab-security/./ok.css', 'lab-security/link.svg', 'lab-security/link-dir/secret.svg',
    'lab-security/code.php', 'lab-security/large.png', 'lab-security/missing.svg',
    '.hidden.svg', '', 'lab-security',
] as $index => $path) {
    $response = $controller->asset($path);
    check($response->getStatus() === 404 && !str_contains($response->render(), 'private-fixture'), 'reject invalid asset case ' . $index);
}

// Exercise Nextcloud's real security middleware with a dummy local user.
// This Request double controls only token and strict-cookie outcomes.
class MissingTokenRequest extends \OC\AppFramework\Http\Request {
    public bool $tokenAccepted = false;
    public function passesStrictCookieCheck(): bool { return true; }
    public function passesCSRFCheck(): bool { return $this->tokenAccepted; }
}
$request = (new ReflectionClass(MissingTokenRequest::class))->newInstanceWithoutConstructor();
$user = Server::get(\OCP\IUserManager::class)->createUser('cadviewer-reader', 'local-isolated-reader');
$session = Server::get(\OCP\IUserSession::class);
$session->setUser($user);
$reflector = $container->get(\OC\AppFramework\Utility\ControllerMethodReflector::class);
$middleware = new \OC\AppFramework\Middleware\Security\SecurityMiddleware(
    $request, $reflector,
    Server::get(\OCP\INavigationManager::class), Server::get(\OCP\IURLGenerator::class),
    Server::get(\Psr\Log\LoggerInterface::class), 'cadviewer_nextcloud', true,
    Server::get(\OCP\IGroupManager::class), Server::get(\OCP\Group\ISubAdmin::class),
    Server::get(\OCP\App\IAppManager::class), $container->get(\OCP\IL10N::class),
    Server::get(\OC\Settings\AuthorizedGroupMapper::class), $session,
    Server::get(\OCP\Security\Ip\IRemoteAddress::class),
);
foreach (['preview'] as $method) {
    $reflector->reflect(ViewerController::class, $method);
    try {
        $middleware->beforeController($controller, $method);
        throw new RuntimeException('CSRF protection did not reject ' . $method);
    } catch (\OC\AppFramework\Middleware\Security\Exceptions\CrossSiteRequestForgeryException $e) {
        check(true, 'missing token rejected for ' . $method);
    }
}
$connection = $container->get(\OCA\CadviewerNextcloud\Controller\ConnectionController::class);
$reflector->reflect(\OCA\CadviewerNextcloud\Controller\ConnectionController::class, 'save');
try {
    $middleware->beforeController($connection, 'save');
    throw new RuntimeException('Reader gained administrative settings');
} catch (\OC\AppFramework\Middleware\Security\Exceptions\NotAdminException $e) {
    check(true, 'reader denied worker configuration');
}
$request->tokenAccepted = true;
foreach (['preview'] as $method) {
    $reflector->reflect(ViewerController::class, $method);
    $middleware->beforeController($controller, $method);
    check(true, 'valid-token middleware control for ' . $method);
}

check(glob($package . '/converter/php/*.php') === [], 'legacy standalone PHP handlers removed');
echo 'PASS focused security regression suite (not a complete app audit)' . PHP_EOL;
