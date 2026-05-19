#!/usr/bin/env python3
"""Generate synthetic italic/oblique Martel Code TTFs from upright TTFs."""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
HINTING_TABLES = ("cvt ", "fpgm", "prep")


@dataclass(frozen=True)
class StyleInfo:
    source_style: str
    italic_style: str
    weight: int


STYLES = {
    "Regular": StyleInfo("Regular", "Italic", 400),
    "DemiBold": StyleInfo("DemiBold", "DemiBold Italic", 600),
    "Bold": StyleInfo("Bold", "Bold Italic", 700),
}


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def set_name(font: TTFont, name_id: int, value: str) -> None:
    for platform_id, plat_enc_id, lang_id in ((3, 1, 0x409), (1, 0, 0)):
        font["name"].setName(value, name_id, platform_id, plat_enc_id, lang_id)


def rename_italic(font: TTFont, family: str, style: str, version: str = "0.2.0") -> None:
    full_name = f"{family} {style}"
    ps_name = f"{family.replace(' ', '')}-{style.replace(' ', '')}"
    set_name(font, 1, family)
    set_name(font, 2, style)
    set_name(font, 3, f"{version};COL;{ps_name}")
    set_name(font, 4, full_name)
    set_name(font, 5, f"Version {version}")
    set_name(font, 6, ps_name)
    set_name(font, 16, family)
    set_name(font, 17, style)


def slant_glyphs(font: TTFont, angle_degrees: float, pivot_y: int) -> None:
    glyf = font["glyf"]
    skew = math.tan(math.radians(abs(angle_degrees)))
    transform = Transform(1, 0, skew, 1, -skew * pivot_y, 0)

    for glyph_name in font.getGlyphOrder():
        old_glyph = glyf[glyph_name]
        old_advance, old_lsb = font["hmtx"].metrics.get(glyph_name, (0, 0))
        pen = TTGlyphPen(glyf)
        old_glyph.draw(TransformPen(pen, transform), glyf)
        new_glyph = pen.glyph()
        glyf[glyph_name] = new_glyph
        if getattr(new_glyph, "numberOfContours", 0) > 0:
            new_glyph.recalcBounds(glyf)
            new_lsb = int(new_glyph.xMin)
        else:
            new_lsb = old_lsb
        if glyph_name in font["hmtx"].metrics:
            font["hmtx"].metrics[glyph_name] = (old_advance, new_lsb)


def mark_italic(font: TTFont, angle_degrees: float, weight: int) -> None:
    if "post" in font:
        font["post"].italicAngle = -abs(angle_degrees)
    if "head" in font:
        font["head"].macStyle |= 0b10
        if weight >= 700:
            font["head"].macStyle |= 0b01
        else:
            font["head"].macStyle &= ~0b01
    if "OS/2" in font:
        font["OS/2"].fsSelection |= 0b1
        font["OS/2"].fsSelection &= ~0b1000000
        font["OS/2"].usWeightClass = weight
    if "hhea" in font:
        font["hhea"].caretSlopeRise = 1000
        font["hhea"].caretSlopeRun = round(math.tan(math.radians(abs(angle_degrees))) * 1000)


def strip_hinting(font: TTFont) -> None:
    for table in HINTING_TABLES:
        if table in font:
            del font[table]


def generate_one(source: Path, out_dir: Path, style_info: StyleInfo, angle: float, family: str, version: str) -> Path:
    font = TTFont(source)
    slant_glyphs(font, angle, pivot_y=0)
    strip_hinting(font)
    mark_italic(font, angle, style_info.weight)
    rename_italic(font, family, style_info.italic_style, version)

    out_name = f"{family.replace(' ', '')}-{style_info.italic_style.replace(' ', '')}.ttf"
    out_path = out_dir / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(out_path, reorderTables=False)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="build/fonts")
    parser.add_argument("--out-dir", default="build/fonts")
    parser.add_argument("--angle", type=float, default=11.0)
    parser.add_argument("--family", default="Martel Code")
    parser.add_argument("--version", default="0.2.0")
    args = parser.parse_args()

    source_dir = resolve(args.source_dir)
    out_dir = resolve(args.out_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing {source_dir}; run `make build` first")

    wrote: list[Path] = []
    for style, style_info in STYLES.items():
        source = source_dir / f"MartelCode-{style}.ttf"
        if not source.exists():
            raise FileNotFoundError(f"Missing upright source font: {source}")
        wrote.append(generate_one(source, out_dir, style_info, args.angle, args.family, args.version))

    for path in wrote:
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
