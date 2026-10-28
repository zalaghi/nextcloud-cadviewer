# Drawing fonts and Persian text

The application interface stays English. Font handling changes only text inside drawings.

## Supplying fonts

Install the font files referenced by your drawings in the worker's private font directory. Both SHX and TrueType fonts can be used by ezdxf. Font files are not included with this project because their redistribution rights vary. A free Liberation Sans fallback is included in the locally built image with its license; a fallback is not an exact replacement for a missing CAD font.

The worker reports missing font names. Warnings may include unused text styles. Obtain the actual matching font from the drawing's author when fidelity matters. Do not rename an unrelated font to hide a warning.

`scripts/prepare-persian-fonts.py SOURCE --stage NEW_DIRECTORY` checks SHX headers/hashes, detects conflicting case-insensitive names and creates byte-identical copies plus lowercase aliases. The destination must be new or empty. It rejects symlink inputs and never executes AutoLISP. Supply TTF fonts separately; the staging helper is specifically for SHX files.

## NASKHD / legacy KATEB-style text

Legacy Persian CAD workflows often store glyph indices rather than modern Unicode text and position or mirror that text in the CAD geometry. Reversing strings or applying a general RTL transformation can damage those drawings.

This project recognizes one byte-identical `naskhd.shx` font by SHA-256:

`2252d08c0d5bc27e5e636dc72529946c0dc8fe8fc5281ba91db2e22839d4696d`

Only styles referencing that verified font receive the compatibility mapping. Unicode characters above byte range are mapped back through Windows-1256, then Windows-1252 where needed. Existing byte-range characters, text order, rotation and mirroring are preserved. The mapping affects an in-memory document only. Unicode/TTF and other SHX styles are left alone. Mixed inline-font MTEXT is skipped.

This fixed missing-glyph boxes in the public NASKHD test sample. The exact authoring tool for every sample entity is not established, and this is not universal KATEB support. Different NASKHD variants, other legacy encodings, bigfonts and modern complex-text shaping require their own evidence and tests. Never expand a font mapping by guessing from its filename alone.

## Acceptance checklist

Use a drawing you can compare with AutoCAD: check representative Persian words, numbers, punctuation, mirrored/rotated labels, text alignment and every important layout. Missing-font substitution and omitted unsupported geometry must not be treated as a correct result. For precise engineering measurements, use the original CAD tool and source dimensions.
