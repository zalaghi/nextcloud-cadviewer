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
| Worker unit/protocol | PASS | 14 tests, including block reuse, missing-font substitution and safe conversion error responses; original coverage: legacy glyph mapping, Unicode style preservation, real multi-layout render metadata, container restrictions, authorization, format/layout/input-size/transfer-encoding checks |
| Font staging | PASS | 6 tests; mislabeled TrueType and corrected-name collisions covered; originals protected, invalid files/symlinks/collisions rejected; no AutoLISP execution |
| Original inputs | PASS | All 20 supplied SHX hashes and both public fixture hashes unchanged |
| npm advisories | 0 reported | npm audit for the current lockfile; not a complete application security audit |
| Python advisories | 0 reported | OSV query for ezdxf 1.4.5, fonttools 4.68.0, numpy 2.5.4, Pillow 13.0.0, pyparsing 3.3.3 and typing_extensions 4.16.0 on the review date |
| AIO app and worker installation | PASS | Native app upgrade, persistent custom-apps directory, rootless worker with enforced limits; 3,795 core/lib/config/.htaccess files unchanged |

The disposable browser test uses an authenticated fixture service returning independently rendered outputs. Separately, deployed DXF and the large private DWG below passed actual authenticated Files sessions through the deployed gateway and rootless parser. The rootless parser was checked on the AIO host with enforced memory/CPU/process limits, read-only filesystem and no network route. The independent OpenRC service is enabled; a host-reboot acceptance test has not been performed. The gateway's protocol tests use a local stub conversion in an isolated loopback namespace; this is not a claim of a production penetration test.

## Persian drawing evidence

The DXF sample originates from [ezdxf discussion 967](https://github.com/mozman/ezdxf/discussions/967), using its [public drawing/font archive](https://github.com/mozman/ezdxf/files/13404548/persian_unicode_text.zip). SHA-256 of the unchanged DXF:

`2700c8eeacf71fef83925074fcc701e4db52ac51e7c4da6ffb5b2c4bff5fab08`

The architectural DWG is the public `maskoni85m(difal.ir).dwg` fixture, obtained from its [public file page](https://s4.picofile.com/file/7953639993/maskoni85m_difal_ir_.rar.html). SHA-256:

`d392a5c562a098cc74dd6a09fa56a02ba03eea2655dab9f1f56564e5446f64a5`

Both use legacy `naskhd.shx` lettering. This demonstrates a concrete legacy Persian SHX workflow; the exact application/AutoLISP used to author every entity is not independently established. Do not label this as proof that every KATEB file works.

The verified NASKHD fingerprint is:

`2252d08c0d5bc27e5e636dc72529946c0dc8fe8fc5281ba91db2e22839d4696d`

For this font only, legacy Unicode code-page artifacts are converted back to SHX byte glyph numbers using Windows-1256, then Windows-1252 fallback. This includes glyphs such as U+0178 and U+017E that previously rendered as boxes. The transformation happens in memory; no drawing, original font, locale or Nextcloud data is rewritten. Text order and CAD rotation/mirroring remain with the drawing/renderer. TTF/other font styles are untouched. Visual inspection confirmed improvement and readable Persian labels; no pixel-perfect comparison with an AutoCAD reference has been completed.

Earlier, before the expanded private font pack and alpha 2 warning filtering, the public samples reported: DXF `arial.ttf`, `romansp.shx`, `romant.shx`; DWG `naskh-h.shx`, `swissl.ttf`. Those earlier warnings could include unused styles. Alpha 2 reports styles used by rendered text only. User-supplied SHX files and downloaded drawings are private test inputs and are excluded from the app/worker distribution. No private customer drawing is included in this validation record.

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

## Alpha 2 regression evidence

A private 12.1 MiB electrical drawing exposed a false font diagnosis: its 225,308 input records exceeded the former 200,000-record limit. Naive block expansion would generate about 3.9 million primitives. Shared block definitions and adjacent-stroke batching produced roughly 28 MiB of SVG with about 28,000 XML elements, 426 definitions and 1,236 references. The release parser completed within its unchanged 2 GiB, 2 CPU, 64-process and 60-CPU-second limits; an isolated host run took 43.6 seconds. This private drawing and the supplied fonts are not redistributed.

A synthetic nested-block fixture compares optimized and ordinary ezdxf rendering, including translation, rotation, colors, layers, paint order and tiny elevation differences. Bounds match, all local references resolve, and the raster comparison had zero pixel difference. This is targeted optimization evidence, not a comparison of the private drawing against AutoCAD.

The large SVG passed the real PHP sanitizer at a 256 MiB PHP memory limit; every path and block reference was retained. Application response tests verify that negotiated gzip reproduces the sanitized vector content exactly, and that `gzip;q=0` is respected. Compression applies only to this app's response.

The same drawing opened visibly in an authenticated Files session on the installed Nextcloud 35.0.2 / PHP 8.4.27 AIO instance. The native app-to-gateway conversion and sanitization took 46.4 seconds in a timed check. Browser zoom and fit worked on the resulting vector drawing. The app and frame both accept the bounded 32 MiB result; content-hashed frame URLs prevent an older cached 16 MiB limit from silently rejecting it. The AIO container/image and 3,795 protected core/config files remained unchanged.

Nine requested font names remained substituted in this drawing: `ARIALN.TTF`, `ARLRDBD.TTF`, `MAIAN.TTF`, `SAS_____.PFB`, `romanc__.ttf`, `romantic.ttf`, `swissl.ttf`, `tahoma.ttf`, and `tahomabd.ttf`. They are absent or unsupported in the provided collection. The drawing opens with a visible English warning; no claim of exact font fidelity is made.

After the expanded pack was installed, both public samples were reopened through the live Files interface: the DXF displayed readable Persian text with no missing-font warning, and the architectural DWG reported only `swissl.ttf`. The viewer defaults to non-scaling one-pixel strokes to keep SHX lettering readable during zoom; Lineweights restores the renderer's stroke widths. The toggle and layers panel were checked in the live browser.

The supplied mixed font pack was inspected without executing Lisp/ARX content. Recognized formats were staged privately; unsupported payloads were reported separately. An offline parser check loaded 563 staged font files, while 78 recognized files had unsupported BIGFONT or malformed font data. These counts describe that private test collection and do not claim universal font support. Missing/unsupported fonts remain visible as non-fatal fidelity warnings.
