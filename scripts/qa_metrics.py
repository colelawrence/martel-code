#!/usr/bin/env python3
"""Metric-level QA for the Martel Code transform."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]

ASCII_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"


def cmap_name(font: TTFont, char: str) -> str | None:
    return (font.getBestCmap() or {}).get(ord(char))


def name_values(font: TTFont, name_id: int) -> set[str]:
    return {str(n.toUnicode()) for n in font["name"].names if n.nameID == name_id}


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/martel-code.json")
    args = parser.parse_args()
    config = json.loads((ROOT / args.config).read_text())
    errors: list[str] = []
    report: dict[str, object] = {"fonts": []}

    for item in config["upstream"]["fonts"]:
        style = item["style"]
        source_path = ROOT / "sources" / "upstream" / item["file"]
        built_path = ROOT / "build" / "fonts" / f"{config['family_name'].replace(' ', '')}-{style.replace(' ', '')}.ttf"
        if not source_path.exists() or not built_path.exists():
            fail(errors, f"missing source/built font for {style}; run make fetch build")
            continue

        source = TTFont(source_path)
        built = TTFont(built_path)
        upem = int(built["head"].unitsPerEm)
        tracking_units = round(float(config["spacing"]["tracking_em"]) * upem)
        space_width = round(float(config["spacing"]["space_width_em"]) * upem)
        punct_width = round(float(config["punctuation"]["normalized_width_em"]) * upem)

        if config["family_name"] not in name_values(built, 1):
            fail(errors, f"{built_path.name}: nameID 1 does not include {config['family_name']}")
        if config["family_name"] not in name_values(built, 16):
            fail(errors, f"{built_path.name}: nameID 16 does not include {config['family_name']}")

        for glyph_name in config["spacing"]["space_glyphs"]:
            if glyph_name in built["hmtx"].metrics:
                actual = built["hmtx"].metrics[glyph_name][0]
                if actual < space_width:
                    fail(errors, f"{built_path.name}:{glyph_name} width {actual} < minimum {space_width}")

        numerals = config.get("numerals", {})
        skip_period_punctuation = bool(numerals.get("tabular", False) and numerals.get("align_period", False))
        for glyph_name in config["punctuation"]["glyphs"]:
            if skip_period_punctuation and glyph_name == "period":
                continue
            if glyph_name in built["hmtx"].metrics:
                actual = built["hmtx"].metrics[glyph_name][0]
                if actual != punct_width:
                    fail(errors, f"{built_path.name}:{glyph_name} width {actual} != expected {punct_width}")

        for ch in ASCII_LETTERS:
            g_src = cmap_name(source, ch)
            g_dst = cmap_name(built, ch)
            if not g_src or not g_dst:
                continue
            old_adv = source["hmtx"].metrics[g_src][0]
            new_adv = built["hmtx"].metrics[g_dst][0]
            if new_adv - old_adv != tracking_units:
                fail(errors, f"{built_path.name}:{ch}/{g_dst} tracking delta {new_adv - old_adv} != {tracking_units}")

        if numerals.get("tabular", False):
            source_char = str(numerals.get("width_source", "0"))
            source_glyph = cmap_name(built, source_char)
            if source_glyph is None:
                fail(errors, f"{built_path.name}: missing tabular width source {source_char!r}")
            else:
                numeral_width = built["hmtx"].metrics[source_glyph][0]
                for ch in str(numerals.get("chars", DIGITS)):
                    glyph = cmap_name(built, ch)
                    if glyph is None:
                        continue
                    actual = built["hmtx"].metrics[glyph][0]
                    if actual != numeral_width:
                        fail(errors, f"{built_path.name}:{ch}/{glyph} width {actual} != tabular width {numeral_width}")
                if numerals.get("align_period", False):
                    period = cmap_name(built, ".")
                    if period is not None:
                        actual = built["hmtx"].metrics[period][0]
                        if actual != numeral_width:
                            fail(errors, f"{built_path.name}:period width {actual} != tabular width {numeral_width}")

        report["fonts"].append({
            "file": str(built_path.relative_to(ROOT)),
            "style": style,
            "upem": upem,
            "tracking_units": tracking_units,
            "space_min_width": space_width,
            "punctuation_width": punct_width,
        })

    out = ROOT / "build" / "reports" / "qa-metrics.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report["ok"] = not errors
    report["errors"] = errors
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
