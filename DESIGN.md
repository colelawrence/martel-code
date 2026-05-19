# Design notes

## Transform ownership

The repo treats upstream Martel TTFs as pinned input artifacts and derives Martel Code via explicit, repeatable metric transforms.

## Current metric policy

- **Family rename:** all generated fonts are renamed to `Martel Code`.
- **Tracking:** Latin letters get `+0.05em` advance by default. The outlines are shifted right by half the added amount so the extra space is distributed on both sides.
- **Spaces:** configured space-like glyphs are widened to at least `0.60em`; already-wider spaces are preserved rather than narrowed. Currently present glyphs include `space`, `uni00A0`, and `uni2007`.
- **Punctuation:** only `period`, `comma`, `colon`, and `semicolon` are normalized to `0.42em` and optically centered by ink bounds. Other punctuation is intentionally left alone until reviewed.
- **Zero:** the `0` cmap glyph gets a centered dot contour with `0.12em` diameter by default, preserving its advance width.
- **Numerals:** `0`–`9` are centered into a tighter explicit `0.62em` tabular cell, and `.` is also centered into that same advance so decimal columns align without excessive numeric side space.

## Why not apply this to all punctuation?

Code punctuation has very different roles: `.` and `,` often want stable spacing in prose/code, but operators (`+`, `=`, `->`), brackets, slashes, quotes, and dashes need separate optical decisions. The config uses a small allowlist so those decisions stay explicit.

## Italic and variable-font workflow

`scripts/generate_italic_fonts.py` creates programmatic oblique companions by shearing generated upright TTF outlines by 11°, updating name/style metadata, marking italic bits, setting `post.italicAngle`, and stripping stale TrueType hinting tables. These files are useful as CSS/editor italic companions, but they are synthetic obliques rather than hand-drawn italics.

`scripts/audit_variable_compatibility.py` checks whether Regular, DemiBold, and Bold can safely interpolate into a `wght` variable font by comparing glyph operation signatures. The current static fonts are not reliable variable-font masters: hundreds of glyphs differ structurally across weights. We should not ship a fake variable font until compatible masters are available.

## README cover workflow

`scripts/generate_cover.py` receives explicit Phosphor / Slime and Phosphor / Tokyo Night Light theme paths from the caller, extracts editor and token colors, then renders a static cover into `assets/martel-code-cover.png` using the generated Martel Code font. The cover generator is intentionally separate from font QA: it is a documentation artifact, not a correctness gate. `make cover` supplies the local default theme paths, but the script itself does not discover sibling repo state by ambient lookup.

## Calibration workflow

`config/calibration.json` is the run-level manifest. It owns the parameter matrix, proof settings, blur radii, and review thresholds. `scripts/calibrate.py` is an orchestrator: it grants paths/config to the narrower worker scripts, but does not own font transforms or image metrics itself.

Boundary split:

- `transform_font.py` owns font metric/name mutation.
- `render_proof.py` owns proof rasterization.
- `blur_qa.py` owns before/after image measurement.
- `kerning_blur_scan.py` owns pair-boundary density measurement.
- `calibrate.py` owns candidate orchestration and summary aggregation.

This keeps each script's needs inside its explicit inputs: no worker script discovers global workflow state by ambient lookup beyond repo-relative path resolution.

## Gaussian blur test

A gaussian blur collapses contour detail into text-color/rhythm information. This repo uses it two ways:

1. before/after proof diffs at multiple radii;
2. pair-boundary density scoring for selected kerning/punctuation pairs.

Negative pair scores indicate unusually open boundaries; positive scores indicate unusually dark/tight boundaries. Scores are review signals, not automatic truth.
