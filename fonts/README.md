# Bundled drawing fonts

These original, unmodified fonts are part of the public repository and are baked into the conversion image. They do not change the English application interface and do not need to be installed on end users' computers.

| Directory | Version | Contents | License |
| --- | --- | --- | --- |
| `vazirmatn/ttf/` | 33.003 | Nine static TrueType weights, Thin through Black | SIL OFL 1.1; `vazirmatn/OFL.txt` and `AUTHORS.txt` |
| `liberation/` | 2.1.5 | Liberation Sans Regular, the existing missing-font fallback | SIL OFL 1.1; `liberation/LICENSE` |

[manifest.json](manifest.json) records the official source, pinned release/commit, byte size and SHA-256 of every font and notice. Vazirmatn files were additionally matched to the upstream Git blob hashes. Liberation Sans Regular is byte-identical to the fallback used in alpha 3. No outlines, names, tables or encodings were modified.

```sh
python3 scripts/prepare-bundled-fonts.py
python3 scripts/prepare-bundled-fonts.py --stage .local/bundled-fonts
```

Run from the repository root. Staging requires a new or empty directory and verifies every file before writing. The worker build stages only this manifest into its image; the corresponding notices and manifest accompany the fonts.

Use the saved filename, for example `Vazirmatn-Regular.ttf`, in a drawing's text style. Vazirmatn is a Unicode font; it is not a substitute for a KATEB/SHX font whose character numbers have a different meaning. Font availability also does not guarantee complex-script shaping fidelity in the renderer.

Additional drawing fonts stay in the administrator's private `/fonts` mount. See [drawing font import](../docs/FONTS.md) and [installation](../docs/INSTALL.md). Do not commit a third-party font pack without a documented redistribution license. A user's drawings and font names may themselves be private.
