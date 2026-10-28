<?php
declare(strict_types=1);
if (getcwd() !== '/scratch/nextcloud') { throw new RuntimeException('Disposable lab only'); }
define('OC_CONSOLE', true);
require getcwd() . '/lib/base.php';
set_exception_handler(static function (Throwable $e): void { fwrite(STDERR, get_class($e) . ': ' . $e->getMessage() . "\n" . $e->getTraceAsString() . "\n"); exit(1); });
use OCP\Server;
use OCA\CadviewerNextcloud\Service\DrawingAccess;
use OCA\CadviewerNextcloud\Service\ConverterClient;
use OCA\CadviewerNextcloud\Service\ViewerSettings;
use OCA\CadviewerNextcloud\Service\DrawingSvg;
use OCA\CadviewerNextcloud\Service\AssetFile;
use OCA\CadviewerNextcloud\Controller\ViewerController;

function verify(bool $condition, string $message): void {
    if (!$condition) { throw new RuntimeException($message); }
    echo 'PASS ' . $message . "\n";
}
class LabConverter extends ConverterClient {
    public int $calls = 0;
    public ?Closure $during = null;
    public function convert(string $drawing, string $extension, int $layoutIndex = 0): string {
        $this->calls++;
        if ($this->during) { ($this->during)(); }
        return '<svg xmlns="http://www.w3.org/2000/svg"><path id="fixture" d="M0 0L10 10"/></svg>';
    }
}
$app = new \OCA\CadviewerNextcloud\AppInfo\Application();
$container = $app->getContainer();
$users = Server::get(\OCP\IUserManager::class);
$session = Server::get(\OCP\IUserSession::class);
$root = Server::get(\OCP\Files\IRootFolder::class);
$alice = $users->createUser('viewer-alice', 'disposable-alice-password');
$bob = $users->createUser('viewer-bob', 'disposable-bob-password');
$session->setUser($alice);
$af = $root->getUserFolder($alice->getUID());
$bf = $root->getUserFolder($bob->getUID());
$a = $af->newFile('plan.DWG', 'AC1021 dummy test drawing');
$b = $bf->newFile('private.dxf', "0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n");
$text = $af->newFile('secret.txt', 'not a CAD file');
$settings = $container->get(ViewerSettings::class);
$converter = new LabConverter($settings);
$access = $container->get(DrawingAccess::class);
$svg = new DrawingSvg();
$controller = new ViewerController(Server::get(\OCP\IRequest::class), $access, $converter, $svg,
    $settings, new AssetFile(), Server::get(\OCP\IURLGenerator::class));
verify($controller->preview($a->getId())->getStatus() === 200, 'owner opens CAD by file ID');
verify($controller->preview($b->getId())->getStatus() === 404, 'another user private file is denied');
verify($controller->preview($text->getId())->getStatus() === 404, 'non-CAD file denied before conversion');
verify($controller->preview(0)->getStatus() === 404, 'invalid file ID denied');
verify($converter->calls === 1, 'denied files never reach conversion');
$response = $controller->preview($a->getId());
verify($response->getHeaders()['Cache-Control'] === 'no-store, private', 'drawing response is never cached');
verify(!str_contains($response->render(), '/scratch/'), 'drawing response contains no filesystem path');
$converter->during = static function () use ($a) { $a->putContent('AC1021 changed during conversion'); };
verify($controller->preview($a->getId())->getStatus() === 409, 'change during conversion discards preview');
$converter->during = null;
$session->setUser($bob);
verify($controller->preview($a->getId())->getStatus() === 404, 'switching users does not reuse previous access');
verify($controller->preview($b->getId())->getStatus() === 200, 'second user opens own CAD');
$session->setUser(null);
verify($controller->preview($b->getId())->getStatus() === 404, 'no session cannot access drawing');
$session->setUser($alice);
$shareManager = Server::get(\OCP\Share\IManager::class);
$share = $shareManager->newShare();
$share->setNode($a)->setShareType(\OCP\Share\IShare::TYPE_USER)->setSharedBy($alice->getUID())
    ->setSharedWith($bob->getUID())->setPermissions(\OCP\Constants::PERMISSION_READ);
$share = $shareManager->createShare($share);
$session->setUser($bob);
// Resolve shares in a fresh mount cache, just as the next HTTP request would.
\OC_Util::tearDownFS();
\OC_Util::setupFS($bob->getUID());
verify($controller->preview($a->getId())->getStatus() === 200, 'read-only shared CAD can be viewed');
$converter->during = static function () use ($shareManager, $share) { $shareManager->deleteShare($share); };
verify($controller->preview($a->getId())->getStatus() === 404, 'revoked share is denied at conversion completion');
$converter->during = null;

$hostile = '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"><script>alert(1)</script>'
    . '<foreignObject><div xmlns="http://www.w3.org/1999/xhtml">unsafe</div></foreignObject>'
    . '<image href="https://example.invalid/tracker"/><path id="kept" d="M0 0L1 1" style="fill:url(https://example.invalid/x)"/>'
    . '<style>@import "https://example.invalid/css";</style></svg>';
$clean = $svg->clean($hostile);
verify(!str_contains($clean, 'script') && !str_contains($clean, 'onload') && !str_contains($clean, 'foreignObject'), 'active SVG content removed');
verify(!str_contains($clean, 'example.invalid') && str_contains($clean, 'id="kept"'), 'external SVG references removed while geometry retained');
try { $svg->clean('<!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]><svg xmlns="http://www.w3.org/2000/svg">&x;</svg>'); throw new RuntimeException('entity accepted'); }
catch (UnexpectedValueException $e) { verify(true, 'SVG entities rejected without loading'); }
$frame = $controller->frame();
$policy = $frame->getHeaders()['Content-Security-Policy'];
verify(str_contains($policy, 'sandbox allow-scripts;') && !str_contains($policy, 'allow-same-origin'), 'viewer frame has opaque origin enforced by response');
verify(str_contains($policy, "default-src 'none'") && !str_contains($policy, 'connect-src *'), 'viewer network restricted to packaged assets');
verify(!str_contains($frame->render(), 'requesttoken'), 'viewer frame receives no Nextcloud token');
verify(str_contains($frame->render(), 'lang="en" dir="ltr"'), 'viewer interface is English');
verify(!str_contains($policy, "'unsafe-eval'") && str_contains($policy, "connect-src 'none'"), 'free viewer uses no eval or outgoing connections');
verify(!str_contains($frame->render(), 'viewer/cadviewer.js'), 'commercial SDK is not loaded');
verify($controller->preview(1, -1)->getStatus() === 400 && $controller->preview(1, 32)->getStatus() === 400, 'layout indices are bounded before reading files');
verify(DrawingAccess::EXTENSIONS === ['dwg', 'dxf'], 'only formats supported by the free engine are advertised');
foreach (['file:///etc/passwd', 'http://example.com/convert', 'https://x/convert?url=file', 'https://a:b@x/convert', "http://127.0.0.1/convert\r\nX:y"] as $endpoint) {
    try { ViewerSettings::validateEndpoint($endpoint); throw new RuntimeException('Unsafe endpoint accepted'); }
    catch (InvalidArgumentException $e) { verify(true, 'unsafe service address rejected'); }
}
$routes = require '/source/appinfo/routes.php';
verify(count($routes['routes']) === 4, 'legacy converter and filesystem routes removed');
$info = simplexml_load_file('/source/appinfo/info.xml');
verify(!isset($info->{'repair-steps'}), 'installation has no core MIME or icon repair steps');
verify(!str_contains(file_get_contents('/source/lib/AppInfo/Application.php'), 'CSPListener'), 'no global CSP weakening registered');
$before = hash_file('sha256', 'custom_apps/cadviewer_nextcloud/js/connection.js');
$listener = $container->get(\OCA\CadviewerNextcloud\Listeners\LoadScriptsListener::class);
$listener->handle(new \OCA\Files\Event\LoadAdditionalScriptsEvent());
verify($before === hash_file('sha256', 'custom_apps/cadviewer_nextcloud/js/connection.js'), 'Files listener does not rewrite JavaScript');
echo "PASS app-only viewer regression suite\n";
