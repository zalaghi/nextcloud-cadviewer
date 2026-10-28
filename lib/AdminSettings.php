<?php
namespace OCA\CadviewerNextcloud;

use OCP\Settings\ISettings;

use OCA\CadviewerNextcloud\Service\ViewerSettings;
use OCP\AppFramework\Http\TemplateResponse;
use OCP\Util;


class AdminSettings implements ISettings {

    public function __construct(private ViewerSettings $settings) {
    }


    public function getForm() {
        Util::addScript('cadviewer_nextcloud', 'connection');
        return new TemplateResponse('cadviewer_nextcloud', 'connection', [
            'endpoint' => $this->settings->endpoint(),
        ]);
    }

    public function getSection() {
        return "cadviewer_nextcloud";
    }

    public function getPriority() {
        return 50;
    }
}
