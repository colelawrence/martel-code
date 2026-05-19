#!/usr/bin/env python3
"""Render deterministic-ish grayscale proof images with Pillow."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", required=True)
    parser.add_argument("--text", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--size", type=int, default=36)
    parser.add_argument("--margin", type=int, default=48)
    parser.add_argument("--line-height", type=float, default=1.35)
    parser.add_argument("--width", type=int, default=1800)
    args = parser.parse_args()

    font_path = resolve(args.font)
    text_path = resolve(args.text)
    out_path = resolve(args.out)
    text = text_path.read_text()
    font = ImageFont.truetype(str(font_path), args.size)

    probe = Image.new("L", (args.width, 100), 255)
    draw = ImageDraw.Draw(probe)
    lines = text.splitlines() or [""]
    line_height = round(args.size * args.line_height)
    height = args.margin * 2 + line_height * len(lines)

    img = Image.new("L", (args.width, height), 255)
    draw = ImageDraw.Draw(img)
    y = args.margin
    for line in lines:
        draw.text((args.margin, y), line, fill=0, font=font)
        y += line_height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
