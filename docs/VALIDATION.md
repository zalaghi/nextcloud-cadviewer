# Validation record — 2026-10-28

This record describes the current free implementation. It does not establish production readiness or universal CAD/Persian fidelity. The original commercial SDK and AutoXChange are absent from active source, dependencies, viewer assets and release inputs. Historic research and proprietary payloads are excluded from this repository.

## Current results

| Check | Result | Scope |
| --- | --- | --- |
| LibreDWG build | PASS | Official 0.14 source SHA-256 verified; built offline with pinned GCC image; standalone `dwg2dxf` |
| Real DXF conversion | PASS | Public ezdxf Persian fixture, original unchanged; ezdxf 1.4.5, private SHX fonts |
| Real DWG conversion | PASS | Public Persian architectural plan, original unchanged; LibreDWG → ezdxf |
| Browser / Files | PASS | Nextcloud 35.0.2, Chromium 151; DXF and DWG default actions, English opaque frame, zoom, fit, layers, monochrome, close, layout error recovery |
| Nextcloud access | PASS | Own-file access, denied other-user files, read-only share, revocation during conversion, changed-file detection, missing session |
| Request/security boundaries | PASS | Native CSRF/admin middleware, SVG active/external content rejection, asset traversal/symlink/size checks, bounded formats/layouts, no eval or drawing network access |
| Core integrity | PASS | 3,793 core/lib/config/.htaccess files identical before enable and after use/disable; browser installation separately matched after use |
| Worker unit/protocol | PASS | 10 tests: legacy glyph mapping, Unicode style preservation, real multi-layout render metadata, container restrictions, authorization, format/layout/input-size/transfer-encoding checks |
| Font staging | PASS | 4 tests; originals protected, invalid files/symlinks/collisions rejected; no AutoLISP execution |
| Original inputs | PASS | All 20 supplied SHX hashes and both public fixture hashes unchanged |
| npm advisories | 0 reported | npm audit for the current lockfile; not a complete application security audit |
| Python advisories | 0 reported | OSV query for ezdxf 1.4.5, fonttools 4.68.0, numpy 2.5.4, Pillow 13.0.0, pyparsing 3.3.3 and typing_extensions 4.16.0 on the review date |
| Production AIO deployment | PENDING | No app or worker deployed; no production core/image/config modifications |

The browser test uses an authenticated fixture service returning independently rendered outputs. The actual rootless parser container was tested separately. The live deployed Nextcloud → gateway → parser path, final host network controls, and unattended service operation are **not yet accepted**. The gateway's request handling was exercised with a local stub conversion in an isolated loopback namespace; this is not a claim of a production penetration test.

## Persian drawing evidence

The DXF sample originates from [ezdxf discussion 967](https://github.com/mozman/ezdxf/discussions/967), using its [public drawing/font archive](https://github.com/mozman/ezdxf/files/13404548/persian_unicode_text.zip). SHA-256 of the unchanged DXF:

`2700c8eeacf71fef83925074fcc701e4db52ac51e7c4da6ffb5b2c4bff5fab08`

The architectural DWG is the public `maskoni85m(difal.ir).dwg` fixture, obtained from its [public file page](https://s4.picofile.com/file/7953639993/maskoni85m_difal_ir_.rar.html). SHA-256:

`d392a5c562a098cc74dd6a09fa56a02ba03eea2655dab9f1f56564e5446f64a5`

Both use legacy `naskhd.shx` lettering. This demonstrates a concrete legacy Persian SHX workflow; the exact application/AutoLISP used to author every entity is not independently established. Do not label this as proof that every KATEB file works.

The verified NASKHD fingerprint is:

`2252d08c0d5bc27e5e636dc72529946c0dc8fe8fc5281ba91db2e22839d4696d`

For this font only, legacy Unicode code-page artifacts are converted back to SHX byte glyph numbers using Windows-1256, then Windows-1252 fallback. This includes glyphs such as U+0178 and U+017E that previously rendered as boxes. The transformation happens in memory; no drawing, original font, locale or Nextcloud data is rewritten. Text order and CAD rotation/mirroring remain with the drawing/renderer. TTF/other font styles are untouched. Visual inspection confirmed improvement and readable Persian labels; no pixel-perfect comparison with an AutoCAD reference has been completed.

Missing fonts reported in the public samples: DXF `arial.ttf`, `romansp.shx`, `romant.shx`; DWG `naskh-h.shx`, `swissl.ttf`. Some warnings may describe unused styles. User-supplied SHX files and downloaded drawings are private test inputs and are excluded from the app/worker distribution. No private customer drawing is included in this validation record.

## Runtime security and operational boundary

The app setup check records the PHP baseline reviewed on 2026-10-28: 8.3.36+, 8.4.27+ or 8.5.12+, and flags enabled session upload progress for review. It does not update PHP or replace regular patch management. The local Nextcloud integration checks use PHP 8.5.12. Deployment-host resource enforcement, private connectivity and real-user acceptance must be verified separately.

## Reproduce local checks

```sh
bash scripts/test-nextcloud.sh
bash scripts/test-worker.sh
bash scripts/test-fixtures.sh
bash scripts/start-browser-lab.sh
# In a separate terminal while the disposable lab is running:
bash scripts/run-browser-check.sh
```

The private font directory and public fixtures must be staged under ignored `.local/` before font/fixture checks. Test scripts intentionally use dummy accounts and isolated, disposable installations. Local logs and screenshots are under `.local/evidence/`; they are excluded from the distributed app. The browser uses replayed actual engine output as described above.
