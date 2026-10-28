<?php

declare(strict_types=1);

namespace OCA\CadviewerNextcloud\SetupCheck;

use OCA\CadviewerNextcloud\Service\PhpRuntime;
use OCP\SetupCheck\ISetupCheck;
use OCP\SetupCheck\SetupResult;

final class PhpRuntimeCheck implements ISetupCheck {
    public function __construct(private PhpRuntime $runtime) {
    }

    public function getCategory(): string {
        return 'security';
    }

    public function getName(): string {
        return 'CADViewer PHP security baseline';
    }

    public function run(): SetupResult {
        if (!$this->runtime->meetsBaseline(PHP_VERSION)) {
            return SetupResult::error(
                'CADViewer requires a reviewed stable PHP branch with the October 2026 security fixes: PHP 8.3.36+, 8.4.27+ or 8.5.12+. Update the server runtime; application code cannot patch PHP.',
                'https://www.php.net/index.php',
            );
        }
        if (filter_var(ini_get('session.upload_progress.enabled'), FILTER_VALIDATE_BOOLEAN)) {
            return SetupResult::warning(
                'PHP meets the reviewed version baseline. Session upload progress is enabled: review the PHP advisory dated 23 October 2026 and disable it at server startup unless required. This check does not establish that the affected serializer transition occurs.',
                'https://www.php.net/index.php',
            );
        }
        return SetupResult::success(
            'PHP meets the version baseline reviewed on ' . PhpRuntime::REVIEWED_ON . '; session upload progress is disabled. This checks runtime prerequisites only, not CADViewer release readiness.',
        );
    }
}
