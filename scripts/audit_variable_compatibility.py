#!/usr/bin/env python3
"""Audit whether Martel Code static TTFs are structurally compatible for a wght variable font."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def recording_signature(font: TTFont, glyph_name: str) -> list[tuple[str, int]]:
    glyph_set = font.getGlyphSet()
    pen = RecordingPen()
    glyph_set[glyph_name].draw(pen)
    return [(operator, len(args)) for operator, args in pen.value]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", nargs="+", default=[
        "fonts/ttf/MartelCode-Regular.ttf",
        "fonts/ttf/MartelCode-DemiBold.ttf",
        "fonts/ttf/MartelCode-Bold.ttf",
    ])
    parser.add_argument("--out", default="build/reports/variable-compatibility.json")
    args = parser.parse_args()

    paths = [resolve(path) for path in args.fonts]
    fonts = [TTFont(path) for path in paths]
    names = [path.name for path in paths]
    glyph_orders = [font.getGlyphOrder() for font in fonts]
    reference_order = glyph_orders[0]

    problems: list[dict[str, Any]] = []
    if any(order != reference_order for order in glyph_orders[1:]):
        problems.append({"type": "glyph_order_mismatch"})

    shared_glyphs = sorted(set.intersection(*(set(order) for order in glyph_orders)))
    missing = sorted(set.union(*(set(order) for order in glyph_orders)) - set(shared_glyphs))
    if missing:
        problems.append({"type": "glyph_set_mismatch", "glyphs": missing[:50], "count": len(missing)})

    incompatible_glyphs = []
    type_counts: Counter[str] = Counter()
    for glyph_name in shared_glyphs:
        signatures = [recording_signature(font, glyph_name) for font in fonts]
        ref = signatures[0]
        if any(signature != ref for signature in signatures[1:]):
            lengths = [len(signature) for signature in signatures]
            if len(set(lengths)) > 1:
                problem_type = "operation_count_mismatch"
            else:
                problem_type = "operation_sequence_mismatch"
            type_counts[problem_type] += 1
            incompatible_glyphs.append({
                "glyph": glyph_name,
                "type": problem_type,
                "operation_counts": dict(zip(names, lengths)),
            })

    report = {
        "ok": not problems and not incompatible_glyphs,
        "fonts": [str(path.relative_to(ROOT)) for path in paths],
        "shared_glyph_count": len(shared_glyphs),
        "incompatible_glyph_count": len(incompatible_glyphs),
        "problem_type_counts": dict(type_counts),
        "problems": problems,
        "sample_incompatible_glyphs": incompatible_glyphs[:100],
        "conclusion": "compatible for a basic wght variable font" if not problems and not incompatible_glyphs else "not compatible enough to build a reliable variable font from current static TTFs",
    }

    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    print(report["conclusion"])
    if incompatible_glyphs:
        print(f"incompatible glyphs: {len(incompatible_glyphs)} / {len(shared_glyphs)}")


if __name__ == "__main__":
    main()
