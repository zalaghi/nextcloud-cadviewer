<?php

declare(strict_types=1);

namespace OCA\CadviewerNextcloud\Service;

/** A dated release prerequisite, not a claim that the application is secure. */
final class PhpRuntime {
    public const REVIEWED_ON = '2026-10-28';
    private const MINIMUM = ['8.3' => '8.3.36', '8.4' => '8.4.27', '8.5' => '8.5.12'];

    public function meetsBaseline(string $version): bool {
        // Accept official stable runtime versions only. Distribution backports
        // and future branches require a separate review; never guess a fix.
        if (!preg_match('/^(8\.[345])\.(\d+)$/D', $version, $match)) {
            return false;
        }
        return version_compare($match[1] . '.' . $match[2], self::MINIMUM[$match[1]], '>=');
    }
}
