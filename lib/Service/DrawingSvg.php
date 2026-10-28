<?php
declare(strict_types=1);
namespace OCA\CadviewerNextcloud\Service;

/** Defense in depth. SVG is displayed only in an opaque-origin sandbox frame. */
class DrawingSvg {
    private const TAGS = ['svg', 'defs', 'style', 'metadata', 'g', 'path', 'text', 'tspan',
        'title', 'desc', 'circle', 'ellipse', 'rect', 'line', 'polyline', 'polygon', 'use',
        'clipPath', 'pattern', 'linearGradient', 'radialGradient', 'stop', 'image', 'a'];

    public function clean(string $svg): string {
        if (strlen($svg) > ConverterClient::MAX_SVG_BYTES) {
            throw new \LengthException('Drawing preview exceeds the size limit.');
        }
        if (stripos($svg, '<!DOCTYPE') !== false || stripos($svg, '<!ENTITY') !== false) {
            throw new \UnexpectedValueException('Invalid drawing preview.');
        }
        $dom = new \DOMDocument();
        $dom->resolveExternals = false;
        $dom->substituteEntities = false;
        $previous = libxml_use_internal_errors(true);
        try {
            $valid = $dom->loadXML($svg, LIBXML_NONET);
        } finally {
            libxml_clear_errors();
            libxml_use_internal_errors($previous);
        }
        if (!$valid || $dom->documentElement?->localName !== 'svg'
            || $dom->documentElement->namespaceURI !== 'http://www.w3.org/2000/svg') {
            throw new \UnexpectedValueException('Invalid drawing preview.');
        }
        $count = 0;
        $nodes = iterator_to_array($dom->getElementsByTagName('*'));
        foreach ($nodes as $node) {
            if (++$count > 250000) {
                throw new \LengthException('Drawing preview is too complex.');
            }
            if ($node->namespaceURI !== 'http://www.w3.org/2000/svg' || !in_array($node->localName, self::TAGS, true)) {
                $node->parentNode?->removeChild($node);
                continue;
            }
            if ($node->localName === 'style' && !$this->safeCss($node->textContent)) {
                $node->parentNode?->removeChild($node);
                continue;
            }
            foreach (iterator_to_array($node->attributes) as $attribute) {
                $name = strtolower($attribute->localName);
                $value = $attribute->value;
                $remove = str_starts_with($name, 'on') || in_array($name, ['base', 'src', 'srcset', 'target'], true);
                if ($name === 'href') {
                    $local = preg_match('/^#[A-Za-z_][A-Za-z0-9_.:-]*$/D', $value);
                    $raster = $node->localName === 'image'
                        && preg_match('~^data:image/(?:png|jpeg|gif);base64,[A-Za-z0-9+/=\r\n]+$~D', $value);
                    $remove = !$local && !$raster;
                }
                if (in_array($name, ['style', 'fill', 'stroke', 'filter', 'clip-path', 'mask', 'cursor'], true)
                    && !$this->safeCss($value)) {
                    $remove = true;
                }
                if ($remove) {
                    $node->removeAttributeNode($attribute);
                }
            }
        }
        // No processing instructions (including xml-stylesheet) or document-level nodes.
        return $dom->saveXML($dom->documentElement);
    }

    private function safeCss(string $css): bool {
        $css = preg_replace('~/\*.*?\*/~s', '', $css);
        // Keep only local fragment paint references. Reject escapes and at-rules.
        $css = preg_replace('/url\(\s*#[A-Za-z_][A-Za-z0-9_.:-]*\s*\)/i', '', $css);
        return !preg_match('/[\\\\@<>]|url\s*\(|expression\s*\(/i', $css);
    }
}
