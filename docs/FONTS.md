# Drawing fonts and Persian text

The application interface stays English. Font handling changes only text inside drawings.

## Supplying fonts

The public repository includes **Vazirmatn 33.003 in all nine static TrueType weights** and **Liberation Sans Regular 2.1.5**. Original files, OFL licenses, authorship and checksums are organized under [fonts/](../fonts/README.md). Every worker build verifies and installs them automatically. End users need no local font installation; the SVG contains drawing outlines.

Use the original filename in a drawing style, for example `Vazirmatn-Regular.ttf` or `Vazirmatn-Bold.ttf`. Availability of a Unicode font does not by itself establish correct Persian/Arabic joining, bidirectional order or CAD layout fidelity. Vazirmatn is not a replacement for legacy KATEB/SHX glyph encodings. These are independent rendering concerns.

Install additional font files referenced by drawings in the worker's private font directory. Both SHX and TrueType fonts can be used by ezdxf. Private font packs are not redistributed: many have no documented permission to publish them. Liberation Sans remains the existing fallback; it is not an exact replacement for a missing CAD font.

The worker substitutes a bundled font when a requested font is missing, malformed or unsupported. It reports affected fonts used by rendered text; unused style definitions do not produce warnings. Missing fonts do not, by themselves, stop the drawing from opening. Obtain the actual matching font from the drawing's author when fidelity matters. Do not rename an unrelated font to hide a warning.

`scripts/prepare-persian-fonts.py SOURCE --stage NEW_DIRECTORY` identifies SHX 1.0/1.1, unifont/bigfont, TrueType, OpenType and font collections by their bytes. It checks size/hash/name collisions and creates byte-identical private copies plus lowercase aliases. A TrueType file incorrectly named `Arial.SHX` is staged as `Arial.ttf`; the original is unchanged. Extensionless drawing references such as `NASKHD` resolve to the actual installed `NASKHD.shx`.

The destination must be new or empty. The default rejects unsupported files. For a mixed font pack, `--skip-invalid` explicitly excludes unsupported files and lists them in the private manifest; collisions and symlinks still fail. Lisp, ARX, executables and other non-font content are never loaded or executed. Identifying a header does not guarantee a complete font: the renderer validates requested fonts and falls back when they cannot be loaded.

AutoCAD BIGFONT rendering is not supported by ezdxf; referenced bigfonts are reported as fidelity limitations. PostScript Type 1/PFB fonts are also not supported by this renderer. Installing more files cannot make unsupported encodings or formats exact. Never suppress a real substitution warning to imply exact fidelity.

## Private import example

Run as the dedicated worker account from the source checkout:

```sh
python3 scripts/prepare-persian-fonts.py /PATH/TO/SUPPLIED/FONTS \
  --skip-invalid --stage "$HOME/cadviewer/fonts-next" \
  > "$HOME/cadviewer/font-import-report.json"
```

Keep the collection under the private `~/cadviewer/` parent (mode 0700). Staged font directories/files are readable by the parser's mapped UID (0755/0644), while the import manifest is private (0600). The source is a single directory of fonts, not a recursive search. Review `rejected` and the staged manifest, preserve the old directory/config for rollback, set the absolute `fonts` path in `~/cadviewer/config.json` to the staged directory and restart the gateway using the host's service manager. Do not overwrite a live font directory piecemeal. The private manifest may contain private filenames and should not be committed to GitHub. Bundled fonts remain available from the image.

## Legacy SHX / KATEB-style text

Legacy Persian CAD workflows often store glyph indices rather than modern Unicode text and position or mirror that text in the CAD geometry. Reversing strings or applying a general RTL transformation can damage those drawings.

Old `AutoCAD-86 shapes 1.0/1.1` fonts whose glyph numbers are all within 0–255 can contain text that was decoded through Windows-1252 during CAD interchange. The renderer recovers a byte only when that byte's glyph actually exists and the original Unicode glyph does not. It also expands supported `%%nnn` decimal glyph references. Unicode SHX, TrueType, missing glyphs and mixed inline-font MTEXT are excluded. This repairs the inspected FARSIN and TRAFIC-B samples without choosing a font by its filename.

Arabic Windows-1256 recovery is more narrowly scoped to one byte-identical `naskhd.shx` font identified by SHA-256:

`2252d08c0d5bc27e5e636dc72529946c0dc8fe8fc5281ba91db2e22839d4696d`

Only styles referencing that verified font receive the additional Windows-1256 mapping. Existing byte-range characters and text order are preserved. Single-line text that omits its own direction inherits the Backwards/Upside Down flags saved in its text style; explicit entity flags, including zero, remain authoritative. MTEXT does not inherit these flags. This honors stored drawing settings without applying a general RTL heuristic. All adjustments affect an in-memory document only.

The initial mapping fixed missing-glyph boxes in the public NASKHD sample. The alpha 3 checks additionally cover FARSIN labels, TRAFIC-B text, decimal glyph escapes and NASKHD style direction in a private electrical drawing. The exact authoring tool for every entity is not established, and this is not universal KATEB support. Different NASKHD variants, other legacy encodings, bigfonts and modern complex-text shaping require their own evidence and tests. Never expand a font mapping by guessing from its filename alone.

## Acceptance checklist

Use a drawing you can compare with AutoCAD: check representative Persian words, numbers, punctuation, mirrored/rotated labels, text alignment and every important layout. Missing-font substitution and omitted unsupported geometry must not be treated as a correct result. For precise engineering measurements, use the original CAD tool and source dimensions.
