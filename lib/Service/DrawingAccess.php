<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Service;

use OCP\Files\File;
use OCP\Files\IRootFolder;
use OCP\Files\NotFoundException;
use OCP\IUserSession;

/** Resolve inside the current user's mounted tree, including shared files. */
class DrawingAccess {
    public const MAX_BYTES = 32 * 1024 * 1024;
    public const EXTENSIONS = ['dwg', 'dxf'];

    public function __construct(private IRootFolder $root, private IUserSession $session) {}

    public function resolve(int $fileId): File {
        $user = $this->session->getUser();
        if ($user === null || $fileId <= 0) {
            throw new NotFoundException('Drawing unavailable');
        }
        $folder = $this->root->getUserFolder($user->getUID());
        foreach ($folder->getById($fileId) as $node) {
            if ($node instanceof File && $node->isReadable()
                && in_array(strtolower(pathinfo($node->getName(), PATHINFO_EXTENSION)), self::EXTENSIONS, true)) {
                return $node;
            }
        }
        throw new NotFoundException('Drawing unavailable');
    }

    public function read(File $file): string {
        if ($file->getSize() > self::MAX_BYTES) {
            throw new \LengthException('Drawings must be 32 MiB or smaller.');
        }
        $stream = $file->fopen('r');
        if (!is_resource($stream)) {
            throw new NotFoundException('Drawing unavailable');
        }
        try {
            $data = stream_get_contents($stream, self::MAX_BYTES + 1);
        } finally {
            fclose($stream);
        }
        if ($data === false || $data === '') {
            throw new NotFoundException('Drawing unavailable');
        }
        if (strlen($data) > self::MAX_BYTES) {
            throw new \LengthException('Drawings must be 32 MiB or smaller.');
        }
        return $data;
    }
}
