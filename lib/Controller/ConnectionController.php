<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Controller;

use OCA\CadviewerNextcloud\Service\ViewerSettings;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\JSONResponse;
use OCP\IRequest;

/** Default Nextcloud middleware requires an administrator and a CSRF token. */
class ConnectionController extends Controller {
    public function __construct(IRequest $request, private ViewerSettings $settings) {
        parent::__construct('cadviewer_nextcloud', $request);
    }

    public function save(string $endpoint, string $token = ''): JSONResponse {
        try {
            $this->settings->save(trim($endpoint), $token);
            return new JSONResponse(['message' => 'CADViewer settings saved.']);
        } catch (\InvalidArgumentException $e) {
            return new JSONResponse(['message' => $e->getMessage()], 400);
        }
    }
}
