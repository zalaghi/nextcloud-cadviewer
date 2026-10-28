<?php

declare(strict_types=1);

namespace OCA\CadviewerNextcloud\AppInfo;

use OCA\CadviewerNextcloud\Listeners\LoadScriptsListener;
use OCA\CadviewerNextcloud\SetupCheck\PhpRuntimeCheck;
use OCA\Files\Event\LoadAdditionalScriptsEvent;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;

class Application extends App implements IBootstrap {
    public const APP_NAME = 'cadviewer_nextcloud';

    public function __construct(array $params = []) {
        parent::__construct(self::APP_NAME, $params);
    }

    public function register(IRegistrationContext $context): void {
        // Setup checks were introduced in Nextcloud 28. Keep bootstrap usable
        // on older installations while the compatibility range is reviewed.
        if (method_exists($context, 'registerSetupCheck')) {
            $context->registerSetupCheck(PhpRuntimeCheck::class);
        }
        $context->registerEventListener(LoadAdditionalScriptsEvent::class, LoadScriptsListener::class);
    }

    public function boot(IBootContext $context): void {
    }
}
