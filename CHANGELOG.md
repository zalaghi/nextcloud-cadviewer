# Changelog

## 0.1.0-alpha.3 — 2026-10-28

- Recover Windows-1252 byte glyphs and decimal `%%nnn` references only for verified old 8-bit SHX formats with the requested glyph present; preserve Unicode fonts and unknown glyphs.
- Honor saved text-style Backwards/Upside Down settings when single-line text omits its own direction; retain explicit entity overrides and leave MTEXT direction unchanged.
- Fix inspected FARSIN, TRAFIC-B and NASKHD title-block text that still displayed incorrectly after the drawing opened.
- Add regression tests for Unicode exclusion, glyph coverage, numeric escapes, style inheritance and explicit overrides.

## 0.1.0-alpha.2 — 2026-10-28

- Reuse repeated block geometry in SVG while preserving paint order, resolved colors, layers and transforms.
- Support larger drawings with bounded input/geometry limits and up to 32 MiB of SVG; retain 2 GiB/2 CPU/64-process parser isolation.
- Resolve installed SHX names without extensions; substitute unavailable or malformed fonts without stopping the entire drawing.
- Report only font limitations affecting rendered text. Identify mislabeled TrueType files in private font packs; report and exclude unsupported files.
- Negotiate lossless gzip for large app preview responses, avoiding oversized browser transfers.
- Match the browser's 32 MiB limit to the server, version frame assets by content, and suppress duplicate requests for the same open file.
- Keep preview strokes thin while zooming so dense plans and SHX lettering stay readable; provide a Lineweights toggle.
- Distinguish complexity, read/conversion, empty-layout and timeout failures from font warnings.
- Add regression coverage for block geometry, font staging/resolution and safe worker errors.

## 0.1.0-alpha.1 — 2026-10-28

Initial public implementation of CADViewer for Nextcloud, with app ID `cadviewer_nextcloud`.

- Open DWG/DXF from Nextcloud Files using current-user permissions.
- Replace commercial SDK/converter components with GNU LibreDWG, ezdxf and an original English SVG viewer.
- Add zoom, pan, fit, layers, layouts, monochrome display and approximate measurement.
- Add a private authenticated gateway with fresh offline rootless parser containers and bounded resources.
- Isolate drawing output in an opaque-origin iframe; sanitize SVG and reject external references.
- Scope legacy Persian byte-glyph recovery to a fingerprinted NASKHD font; preserve source drawings/fonts.
- Remove legacy filesystem endpoints, MIME repair steps, global CSP weakening and core/image edits.
- Add focused access/security tests, real DWG/DXF conversion evidence, font-staging tests and browser integration checks.

Alpha limitations and deployment acceptance status are recorded in docs/VALIDATION.md. This release is not listed in the Nextcloud app store and is installed manually for testing.
