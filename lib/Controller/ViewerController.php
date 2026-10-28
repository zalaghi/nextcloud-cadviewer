<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Controller;

use OCA\CadviewerNextcloud\Service\AssetFile;
use OCA\CadviewerNextcloud\Service\ConverterClient;
use OCA\CadviewerNextcloud\Service\ConversionException;
use OCA\CadviewerNextcloud\Service\DrawingAccess;
use OCA\CadviewerNextcloud\Service\DrawingSvg;
use OCA\CadviewerNextcloud\Service\ViewerSettings;
use OCP\AppFramework\Controller;
use OCP\AppFramework\Http\Attribute\NoAdminRequired;
use OCP\AppFramework\Http\Attribute\NoCSRFRequired;
use OCP\AppFramework\Http\Attribute\PublicPage;
use OCP\AppFramework\Http\Attribute\NoSameSiteCookieRequired;
use OCP\AppFramework\Http\DataDisplayResponse;
use OCP\AppFramework\Http\EmptyContentSecurityPolicy;
use OCP\AppFramework\Http\JSONResponse;
use OCP\Files\NotFoundException;
use OCP\Files\NotPermittedException;
use OCP\IRequest;
use OCP\IURLGenerator;

class ViewerController extends Controller {
    public function __construct(IRequest $request, private DrawingAccess $files,
        private ConverterClient $converter, private DrawingSvg $svg,
        private ViewerSettings $settings, private AssetFile $assets, private IURLGenerator $url) {
        parent::__construct('cadviewer_nextcloud', $request);
    }

    #[NoAdminRequired]
    public function preview(int $fileId, int $layoutIndex = 0): JSONResponse|DataDisplayResponse {
        if ($layoutIndex < 0 || $layoutIndex > 31) {
            return $this->result(['message' => 'Invalid layout.'], 400);
        }
        try {
            $file = $this->files->resolve($fileId);
            $etag = $file->getEtag();
            $content = $this->files->read($file);
            $extension = strtolower(pathinfo($file->getName(), PATHINFO_EXTENSION));
            $drawing = $this->svg->clean($this->converter->convert($content, $extension, $layoutIndex));
            // A conversion may take a minute. Check permission and file version again.
            $current = $this->files->resolve($fileId);
            if ($current->getEtag() !== $etag
                || !hash_equals(hash('sha256', $content), hash('sha256', $this->files->read($current)))) {
                return $this->result(['message' => 'The drawing changed. Please open it again.'], 409);
            }
            return $this->drawingResult($drawing);
        } catch (NotFoundException | NotPermittedException $e) {
            return $this->result(['message' => 'Drawing unavailable or access denied.'], 404);
        } catch (\LengthException $e) {
            return $this->result(['message' => $e->getMessage()], 413);
        } catch (ConversionException $e) {
            return $this->result(['message' => $e->getMessage()], 422);
        } catch (\Throwable $e) {
            return $this->result(['message' => 'CADViewer could not open this drawing. Please check the conversion service.'], 503);
        }
    }

    private function result(array $data, int $status = 200): JSONResponse {
        return new JSONResponse($data, $status, ['Cache-Control' => 'no-store, private',
            'X-Content-Type-Options' => 'nosniff']);
    }

    private function drawingResult(string $drawing): JSONResponse|DataDisplayResponse {
        // Compress only this app's successful preview response. Native browser
        // decoding avoids large transfers without changing Nextcloud/web-server
        // configuration or the drawing's vector geometry.
        $gzip = false;
        foreach (explode(',', strtolower($this->request->getHeader('Accept-Encoding'))) as $encoding) {
            if (preg_match('/^\s*gzip\s*(?:;\s*q=(0(?:\.\d+)?|1(?:\.0+)?))?\s*$/D', $encoding, $match)) {
                $gzip = !isset($match[1]) || (float)$match[1] > 0;
                break;
            }
        }
        if (!$gzip || strlen($drawing) < 65536) {
            return $this->result(['svg' => $drawing]);
        }
        $json = json_encode(['svg' => $drawing], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
        $compressed = gzencode($json, 4);
        if ($compressed === false) {
            throw new \RuntimeException('Preview compression failed.');
        }
        return new DataDisplayResponse($compressed, 200, [
            'Content-Type' => 'application/json; charset=utf-8',
            'Content-Encoding' => 'gzip', 'Vary' => 'Accept-Encoding',
            'Cache-Control' => 'no-store, private', 'X-Content-Type-Options' => 'nosniff',
        ]);
    }

    // This page contains only the shipped viewer, never user data or credentials.
    #[PublicPage]
    #[NoCSRFRequired]
    #[NoSameSiteCookieRequired]
    public function frame(): DataDisplayResponse {
        $base = $this->url->linkToRouteAbsolute('cadviewer_nextcloud.viewer.asset', ['path' => 'viewer/frame.js']);
        $base = substr($base, 0, -strlen('viewer/frame.js'));
        $safe = htmlspecialchars($base, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        $version = substr(hash('sha256', ($this->assets->read('viewer/frame.js')['content'] ?? '')
            . ($this->assets->read('viewer/frame.css')['content'] ?? '')), 0, 16);
        $html = '<!doctype html><html lang="en" dir="ltr"><head><meta charset="utf-8">'
            . '<meta name="referrer" content="no-referrer"><title>CADViewer</title>'
            . '<link rel="stylesheet" href="' . $safe . 'viewer/frame.css?v=' . $version . '">'
            . '</head><body><main id="viewer"></main>'
            . '<script src="' . $safe . 'viewer/frame.js?v=' . $version . '"></script></body></html>';
        $response = new DataDisplayResponse($html, 200, ['Content-Type' => 'text/html; charset=UTF-8',
            'Cache-Control' => 'no-store', 'Referrer-Policy' => 'no-referrer',
            'X-Content-Type-Options' => 'nosniff']);
        // Empty policy intentionally prevents global policy merging. This stricter
        // policy applies only to this inert, credential-free, sandboxed viewer page.
        $response->setContentSecurityPolicy(new EmptyContentSecurityPolicy());
        $response->addHeader('Content-Security-Policy', "default-src 'none'; sandbox allow-scripts; "
            . "script-src $base; style-src $base 'unsafe-inline'; "
            . "img-src data:; font-src 'none'; connect-src 'none'; "
            . "frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'");
        return $response;
    }

    #[PublicPage]
    #[NoCSRFRequired]
    #[NoSameSiteCookieRequired]
    public function asset(string $path): DataDisplayResponse {
        $asset = $this->assets->read($path);
        return new DataDisplayResponse($asset['content'] ?? '', $asset === null ? 404 : 200, [
            'Content-Type' => $asset['type'] ?? 'text/plain', 'X-Content-Type-Options' => 'nosniff',
            'Cache-Control' => 'public, max-age=3600', 'Access-Control-Allow-Origin' => '*',
            'Cross-Origin-Resource-Policy' => 'cross-origin',
        ]);
    }
}
