<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Service;

/** Fixed administrator-selected service. No user URLs, redirects or parameters. */
class ConverterClient {
    public const MAX_SVG_BYTES = 32 * 1024 * 1024;
    public function __construct(private ViewerSettings $settings) {}

    public function convert(string $drawing, string $extension, int $layoutIndex = 0): string {
        $endpoint = $this->settings->endpoint();
        $token = $this->settings->token();
        if ($endpoint === '' || $token === '') {
            throw new \RuntimeException('CADViewer conversion service is not configured.');
        }
        ViewerSettings::validateEndpoint($endpoint);
        if (!in_array($extension, DrawingAccess::EXTENSIONS, true) || $layoutIndex < 0 || $layoutIndex > 31) {
            throw new \InvalidArgumentException('Unsupported drawing type.');
        }
        $body = '';
        $curl = curl_init($endpoint);
        curl_setopt_array($curl, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $drawing,
            CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . $token,
                'Content-Type: application/octet-stream', 'Accept: image/svg+xml',
                'Accept-Encoding: identity', 'X-CAD-Format: ' . $extension, 'X-CAD-Layout: ' . $layoutIndex, 'Expect:'],
            CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 90,
            CURLOPT_FOLLOWLOCATION => false, CURLOPT_MAXREDIRS => 0,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_PROXY => '', CURLOPT_SSL_VERIFYPEER => true, CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_WRITEFUNCTION => static function ($handle, string $chunk) use (&$body): int {
                if (strlen($body) + strlen($chunk) > self::MAX_SVG_BYTES) {
                    return 0;
                }
                $body .= $chunk;
                return strlen($chunk);
            },
        ]);
        try {
            $success = curl_exec($curl);
            $status = curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
            $type = curl_getinfo($curl, CURLINFO_CONTENT_TYPE);
        } finally {
            // PHP 8.5 releases CurlHandle automatically; curl_close is deprecated.
            unset($curl);
        }
        if ($status === 429 || $status === 503) {
            throw ConversionException::fromCode('busy');
        }
        if ($success === false || $status !== 200 || $type !== 'image/svg+xml' || $body === '') {
            // Never disclose worker output, credentials, paths or cURL diagnostics.
            $error = strlen($body) <= 200 ? json_decode($body, true, 4) : null;
            throw ConversionException::fromCode(is_array($error) && is_string($error['error'] ?? null)
                ? $error['error'] : 'conversion_failed');
        }
        return $body;
    }
}
