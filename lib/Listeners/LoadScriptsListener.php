<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Listeners;

use OCA\Files\Event\LoadAdditionalScriptsEvent;
use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;
use OCP\Util;

/** Register packaged assets without changing core, configuration or app files. */
class LoadScriptsListener implements IEventListener {
    public function handle(Event $event): void {
        if ($event instanceof LoadAdditionalScriptsEvent) {
            Util::addScript('cadviewer_nextcloud', 'cadviewer-files');
            Util::addStyle('cadviewer_nextcloud', 'viewer');
        }
    }
}
