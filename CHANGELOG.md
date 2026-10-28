# Changelog

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
