<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Service;

use OCP\IConfig;
use OCP\Security\ICrypto;

class ViewerSettings {
    public function __construct(private IConfig $config, private ICrypto $crypto) {}

    public static function validateEndpoint(string $endpoint): void {
        $url = parse_url($endpoint);
        if ($url === false || !isset($url['scheme'], $url['host'])
            || !in_array($url['scheme'], ['http', 'https'], true)
            || ($url['path'] ?? '') !== '/convert'
            || isset($url['user']) || isset($url['pass']) || isset($url['query']) || isset($url['fragment'])
            || preg_match('/[\x00-\x20\x7f\\\\]/', $endpoint)) {
            throw new \InvalidArgumentException('Use an HTTP(S) converter URL ending in /convert, without credentials or query parameters.');
        }
        // Plain HTTP is permitted only on private addresses or a Docker DNS name.
        $host = $url['host'];
        $private = preg_match('/^(?:127\.|10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)/', $host)
            && filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_IPV4);
        $internalName = preg_match('/^[a-zA-Z][a-zA-Z0-9-]*$/D', $host);
        if ($url['scheme'] === 'http' && !$private && !$internalName) {
            throw new \InvalidArgumentException('Use HTTPS outside a private network.');
        }
    }

    public function endpoint(): string {
        return $this->config->getAppValue('cadviewer_nextcloud', 'worker_endpoint', '');
    }

    public function token(): string {
        $value = $this->config->getAppValue('cadviewer_nextcloud', 'worker_token', '');
        return $value === '' ? '' : $this->crypto->decrypt($value);
    }

    public function save(string $endpoint, string $token): void {
        self::validateEndpoint($endpoint);
        if (($token !== '' && !preg_match('/^[A-Za-z0-9_-]{43,128}$/D', $token))
            || ($token === '' && $this->token() === '')) {
            throw new \InvalidArgumentException('Provide a worker token of at least 43 URL-safe characters.');
        }
        // Persist app configuration only; never modify config.php or core files.
        $this->config->setAppValue('cadviewer_nextcloud', 'worker_endpoint', $endpoint);
        if ($token !== '') {
            $this->config->setAppValue('cadviewer_nextcloud', 'worker_token', $this->crypto->encrypt($token));
        }
    }
}
