<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Service;

/** Only fixed public messages cross the private converter boundary. */
class ConversionException extends \RuntimeException {
    public static function fromCode(string $code): self {
        return new self(match ($code) {
            'drawing_limit', 'resource_limit' => 'This drawing exceeds the supported preview complexity. Its fonts are not the cause of this error.',
            'empty_layout' => 'This layout contains no visible geometry. Please select another layout.',
            'conversion_timeout' => 'This drawing took too long to convert. Please try a smaller drawing or another layout.',
            'invalid_drawing' => 'The drawing could not be read. It may be damaged or contain unsupported CAD data.',
            'busy' => 'CADViewer is busy. Please try again shortly.',
            default => 'The drawing could not be converted. Please contact your administrator.',
        });
    }
}
