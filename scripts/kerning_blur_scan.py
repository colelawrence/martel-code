#!/usr/bin/env python3
"""Gaussian-blur kerning/rhythm scan for selected pairs.

For each pair, render a repeated context, blur it, then inspect the vertical ink-density
near the pair boundary. The score is relative to that sample's median column density:
negative means unusually open/light; positive means unusually tight/dark.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_pairs(path: Path) -> list[str]:
    pairs: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pairs.append(line)
    return pairs


def render_text(font: ImageFont.FreeTypeFont, text: str, size: int, margin: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    width = int(font.getlength(text)) + margin * 2 + size * 2
    height = int(size * 2.4)
    img = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(img)
    draw.text((margin, margin // 2), text, fill=0, font=font)
    return img, draw


def density_score(img: Image.Image, boundary_x: int, band: int, crop_top: int, crop_bottom: int) -> dict[str, float]:
    blurred = img.filter(ImageFilter.GaussianBlur(3.0))
    arr = np.asarray(blurred.crop((0, crop_top, blurred.width, crop_bottom)), dtype=np.float32)
    ink = 1.0 - (arr / 255.0)
    column_density = ink.mean(axis=0)
    usable = column_density[column_density > 0.01]
    median = float(np.median(usable)) if usable.size else 0.0
    std = float(np.std(usable)) if usable.size else 0.0
    lo = max(0, boundary_x - band)
    hi = min(len(column_density), boundary_x + band + 1)
    boundary = column_density[lo:hi]
    boundary_mean = float(boundary.mean()) if boundary.size else 0.0
    z = (boundary_mean - median) / std if std > 1e-6 else 0.0
    return {
        "boundary_density": boundary_mean,
        "median_density": median,
        "std_density": std,
        "z_score": float(z),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", required=True)
    parser.add_argument("--pairs", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--size", type=int, default=72)
    parser.add_argument("--margin", type=int, default=48)
    parser.add_argument("--band", type=int, default=8)
    args = parser.parse_args()

    font_path = resolve(args.font)
    pairs_path = resolve(args.pairs)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(font_path), args.size)
    label_font = ImageFont.load_default()

    rows: list[dict[str, object]] = []
    rendered: list[tuple[str, Image.Image, dict[str, float]]] = []
    prefix = "nnn"
    suffix = "nnn"

    for pair in load_pairs(pairs_path):
        if len(pair) < 2:
            continue
        first = pair[0]
        text = f"{prefix}{pair}{suffix}"
        img, draw = render_text(font, text, args.size, args.margin)
        boundary_x = round(args.margin + draw.textlength(prefix + first, font=font))
        score = density_score(img, boundary_x, args.band, args.margin // 2, img.height - args.margin // 3)
        row = {"pair": pair, "sample": text, "boundary_x": boundary_x, **score}
        rows.append(row)
        rendered.append((pair, img, score))

    rows.sort(key=lambda r: abs(float(r["z_score"])), reverse=True)

    csv_path = out_dir / "kerning-blur-scan.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["pair", "sample", "boundary_x", "boundary_density", "median_density", "std_density", "z_score"])
        writer.writeheader()
        writer.writerows(rows)

    (out_dir / "kerning-blur-scan.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")

    # Contact sheet in original pair order for visual review.
    if rendered:
        w = max(img.width for _pair, img, _score in rendered) + 260
        h = sum(img.height for _pair, img, _score in rendered)
        sheet = Image.new("L", (w, h), 255)
        y = 0
        draw_sheet = ImageDraw.Draw(sheet)
        for pair, img, score in rendered:
            sheet.paste(img, (0, y))
            draw_sheet.text((img.width + 12, y + 20), f"{pair}  z={score['z_score']:.2f}", fill=0, font=label_font)
            y += img.height
        sheet.save(out_dir / "kerning-blur-contact-sheet.png")

    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
