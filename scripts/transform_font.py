#!/usr/bin/env python3
"""Build Martel Code by applying scripted spacing and naming transforms to Martel TTFs.

The transform is intentionally conservative:
- rename the family to avoid OFL reserved-name ambiguity;
- widen selected space glyphs;
- normalize only the configured punctuation glyphs;
- add default tracking to Latin letters/digits by widening advances and shifting ink.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]

LATIN_UPPER = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
LATIN_LOWER = [chr(c) for c in range(ord("a"), ord("z") + 1)]
DIGITS = [chr(c) for c in range(ord("0"), ord("9") + 1)]


@dataclass(frozen=True)
class FontItem:
    file: str
    style: str
    weight: int


def glyph_name_for_char(font: TTFont, char: str) -> str | None:
    return (font.getBestCmap() or {}).get(ord(char))


def glyph_names_for_chars(font: TTFont, chars: Iterable[str]) -> set[str]:
    cmap = font.getBestCmap() or {}
    return {cmap[ord(ch)] for ch in chars if ord(ch) in cmap}


def configured_tracking_glyphs(font: TTFont, sets: list[str]) -> set[str]:
    names: set[str] = set()
    if "latin_letters" in sets:
        names |= glyph_names_for_chars(font, LATIN_UPPER + LATIN_LOWER)
    if "digits" in sets:
        names |= glyph_names_for_chars(font, DIGITS)
    return names


def glyph_bounds(font: TTFont, glyph_name: str) -> tuple[int, int] | None:
    glyf = font["glyf"]
    glyph = glyf[glyph_name]
    if glyph.isComposite():
        glyph.recalcBounds(glyf)
    elif getattr(glyph, "numberOfContours", 0) > 0:
        glyph.recalcBounds(glyf)
    if not hasattr(glyph, "xMin") or not hasattr(glyph, "xMax"):
        return None
    return int(glyph.xMin), int(glyph.xMax)


def glyph_bounds_xy(font: TTFont, glyph_name: str) -> tuple[int, int, int, int] | None:
    glyf = font["glyf"]
    glyph = glyf[glyph_name]
    if glyph.isComposite() or getattr(glyph, "numberOfContours", 0) > 0:
        glyph.recalcBounds(glyf)
    if not all(hasattr(glyph, attr) for attr in ("xMin", "yMin", "xMax", "yMax")):
        return None
    return int(glyph.xMin), int(glyph.yMin), int(glyph.xMax), int(glyph.yMax)


def shift_glyph_x(font: TTFont, glyph_name: str, dx: int) -> None:
    if dx == 0:
        return
    glyf = font["glyf"]
    glyph = glyf[glyph_name]
    if glyph.isComposite():
        for component in glyph.components:
            component.x += dx
    elif getattr(glyph, "numberOfContours", 0) > 0:
        glyph.coordinates.translate((dx, 0))
    glyph.recalcBounds(glyf)


def set_centered_advance(font: TTFont, glyph_name: str, new_advance: int) -> None:
    hmtx = font["hmtx"].metrics
    bounds = glyph_bounds(font, glyph_name)
    if bounds is None:
        hmtx[glyph_name] = (new_advance, 0)
        return

    x_min, x_max = bounds
    ink_width = x_max - x_min
    desired_lsb = round((new_advance - ink_width) / 2)
    shift_glyph_x(font, glyph_name, desired_lsb - x_min)
    bounds_after = glyph_bounds(font, glyph_name)
    hmtx[glyph_name] = (new_advance, bounds_after[0] if bounds_after else 0)


def add_tracking(font: TTFont, glyph_names: set[str], tracking_units: int) -> dict[str, dict[str, int]]:
    changed: dict[str, dict[str, int]] = {}
    hmtx = font["hmtx"].metrics
    half = tracking_units // 2
    for glyph_name in sorted(glyph_names):
        if glyph_name not in hmtx:
            continue
        old_adv, old_lsb = hmtx[glyph_name]
        bounds = glyph_bounds(font, glyph_name)
        if bounds is None:
            continue
        shift_glyph_x(font, glyph_name, half)
        bounds_after = glyph_bounds(font, glyph_name)
        new_adv = old_adv + tracking_units
        new_lsb = bounds_after[0] if bounds_after else old_lsb + half
        hmtx[glyph_name] = (new_adv, new_lsb)
        changed[glyph_name] = {"old_advance": old_adv, "new_advance": new_adv, "delta": tracking_units}
    return changed


def set_space_widths(font: TTFont, space_names: list[str], min_width: int) -> dict[str, dict[str, int]]:
    changed: dict[str, dict[str, int]] = {}
    hmtx = font["hmtx"].metrics
    for glyph_name in space_names:
        if glyph_name not in hmtx:
            continue
        old_adv, old_lsb = hmtx[glyph_name]
        new_width = max(old_adv, min_width)
        hmtx[glyph_name] = (new_width, old_lsb)
        changed[glyph_name] = {"old_advance": old_adv, "new_advance": new_width, "min_advance": min_width}
    return changed


def normalize_punctuation(font: TTFont, glyph_names: list[str], new_width: int) -> dict[str, dict[str, int]]:
    changed: dict[str, dict[str, int]] = {}
    hmtx = font["hmtx"].metrics
    for glyph_name in glyph_names:
        if glyph_name not in hmtx:
            continue
        old_adv, _old_lsb = hmtx[glyph_name]
        set_centered_advance(font, glyph_name, new_width)
        new_adv, new_lsb = hmtx[glyph_name]
        changed[glyph_name] = {"old_advance": old_adv, "new_advance": new_adv, "new_lsb": new_lsb}
    return changed


def add_dotted_zero(font: TTFont, diameter: int) -> dict[str, int | str] | None:
    glyph_name = glyph_name_for_char(font, "0")
    if glyph_name is None or glyph_name not in font["glyf"] or glyph_name not in font["hmtx"].metrics:
        return None

    bounds = glyph_bounds_xy(font, glyph_name)
    if bounds is None:
        return None

    glyf = font["glyf"]
    old_glyph = glyf[glyph_name]
    old_advance, old_lsb = font["hmtx"].metrics[glyph_name]
    x_min, y_min, x_max, y_max = bounds
    radius = max(1, round(diameter / 2))
    cx = round((x_min + x_max) / 2)
    cy = round((y_min + y_max) / 2)

    pen = TTGlyphPen(glyf)
    old_glyph.draw(pen, glyf)
    pen.moveTo((cx, cy + radius))
    pen.qCurveTo((cx + radius, cy + radius), (cx + radius, cy))
    pen.qCurveTo((cx + radius, cy - radius), (cx, cy - radius))
    pen.qCurveTo((cx - radius, cy - radius), (cx - radius, cy))
    pen.qCurveTo((cx - radius, cy + radius), (cx, cy + radius))
    pen.closePath()

    new_glyph = pen.glyph()
    glyf[glyph_name] = new_glyph
    new_glyph.recalcBounds(glyf)
    font["hmtx"].metrics[glyph_name] = (old_advance, new_glyph.xMin if hasattr(new_glyph, "xMin") else old_lsb)
    return {
        "glyph": glyph_name,
        "advance": old_advance,
        "old_lsb": old_lsb,
        "new_lsb": font["hmtx"].metrics[glyph_name][1],
        "center_x": cx,
        "center_y": cy,
        "diameter": diameter,
    }


def set_tabular_numerals(
    font: TTFont,
    chars: str,
    width_source: str,
    align_period: bool,
    target_width: int | None,
) -> dict[str, object] | None:
    source_glyph = glyph_name_for_char(font, width_source)
    if target_width is None:
        if source_glyph is None or source_glyph not in font["hmtx"].metrics:
            return None
        target_width = font["hmtx"].metrics[source_glyph][0]
    changed: dict[str, dict[str, int | str]] = {}
    target_chars = list(chars) + (["."] if align_period else [])
    for char in target_chars:
        glyph_name = glyph_name_for_char(font, char)
        if glyph_name is None or glyph_name not in font["hmtx"].metrics:
            continue
        old_advance, old_lsb = font["hmtx"].metrics[glyph_name]
        set_centered_advance(font, glyph_name, target_width)
        new_advance, new_lsb = font["hmtx"].metrics[glyph_name]
        changed[char] = {
            "glyph": glyph_name,
            "old_advance": old_advance,
            "new_advance": new_advance,
            "old_lsb": old_lsb,
            "new_lsb": new_lsb,
        }

    return {
        "width_source": width_source,
        "source_glyph": source_glyph,
        "target_width": target_width,
        "align_period": align_period,
        "changed": changed,
    }


def set_name(font: TTFont, name_id: int, value: str) -> None:
    name_table = font["name"]
    for platform_id, plat_enc_id, lang_id in ((3, 1, 0x409), (1, 0, 0)):
        name_table.setName(value, name_id, platform_id, plat_enc_id, lang_id)


def rename_font(font: TTFont, family: str, style: str, version: str) -> None:
    full_name = family if style == "Regular" else f"{family} {style}"
    ps_style = style.replace(" ", "")
    ps_name = f"{family.replace(' ', '')}-{ps_style}"
    unique_id = f"{version};COL;{ps_name}"

    set_name(font, 1, family)
    set_name(font, 2, style)
    set_name(font, 3, unique_id)
    set_name(font, 4, full_name)
    set_name(font, 5, f"Version {version}")
    set_name(font, 6, ps_name)
    set_name(font, 16, family)
    set_name(font, 17, style)


def transform_one(config: dict, item: FontItem, font_dir: Path, report_dir: Path) -> tuple[Path, Path]:
    source = ROOT / "sources" / "upstream" / item.file
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}; run `make fetch` first")

    font = TTFont(source)
    upem = int(font["head"].unitsPerEm)
    spacing = config["spacing"]
    punctuation = config["punctuation"]

    report: dict[str, object] = {
        "source": str(source.relative_to(ROOT)),
        "style": item.style,
        "weight": item.weight,
        "unitsPerEm": upem,
        "changes": {},
    }

    tracking_units = round(float(spacing["tracking_em"]) * upem)
    tracking_names = configured_tracking_glyphs(font, spacing["tracking_glyph_sets"])
    report["changes"]["tracking"] = add_tracking(font, tracking_names, tracking_units)

    space_width = round(float(spacing["space_width_em"]) * upem)
    report["changes"]["spaces"] = set_space_widths(font, spacing["space_glyphs"], space_width)

    punctuation_width = round(float(punctuation["normalized_width_em"]) * upem)
    report["changes"]["punctuation"] = normalize_punctuation(font, punctuation["glyphs"], punctuation_width)

    zero = config.get("zero", {})
    if zero.get("dot", False):
        diameter = round(float(zero.get("dot_diameter_em", 0.12)) * upem)
        report["changes"]["zero"] = add_dotted_zero(font, diameter)

    numerals = config.get("numerals", {})
    if numerals.get("tabular", False):
        numeral_width = round(float(numerals["width_em"]) * upem) if "width_em" in numerals else None
        report["changes"]["numerals"] = set_tabular_numerals(
            font,
            str(numerals.get("chars", "0123456789")),
            str(numerals.get("width_source", "0")),
            bool(numerals.get("align_period", False)),
            numeral_width,
        )

    rename_font(font, config["family_name"], item.style, config["version"])

    # Mark modified fonts as installable and update OS/2 weight metadata.
    if "OS/2" in font:
        font["OS/2"].fsType = 0
        font["OS/2"].usWeightClass = item.weight

    output_name = f"{config['family_name'].replace(' ', '')}-{item.style.replace(' ', '')}.ttf"
    out_path = font_dir / output_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(out_path)

    report_path = report_dir / f"{out_path.stem}.metrics.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path}")
    print(f"wrote {report_path}")
    return out_path, report_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/martel-code.json")
    parser.add_argument("--out-font-dir", default="build/fonts")
    parser.add_argument("--report-dir", default="build/reports")
    parser.add_argument("--styles", default=None, help="Comma-separated style filter, e.g. Regular,Bold")
    args = parser.parse_args()
    config = json.loads((ROOT / args.config).read_text())
    font_dir = Path(args.out_font_dir)
    report_dir = Path(args.report_dir)
    if not font_dir.is_absolute():
        font_dir = ROOT / font_dir
    if not report_dir.is_absolute():
        report_dir = ROOT / report_dir
    styles = {style.strip() for style in args.styles.split(",")} if args.styles else None
    for raw in config["upstream"]["fonts"]:
        item = FontItem(**raw)
        if styles is not None and item.style not in styles:
            continue
        transform_one(config, item, font_dir, report_dir)


if __name__ == "__main__":
    main()
