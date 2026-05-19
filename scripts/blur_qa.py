#!/usr/bin/env python3
"""Compare proof renders with raw and multi-scale gaussian-blur diffs.

This is for review, not an absolute pass/fail oracle: raw diff shows contour changes;
blurred diffs expose rhythm/text-color changes while suppressing antialias noise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_pair(before_path: Path, after_path: Path) -> tuple[Image.Image, Image.Image]:
    before = Image.open(before_path).convert("L")
    after = Image.open(after_path).convert("L")
    width = max(before.width, after.width)
    height = max(before.height, after.height)

    def pad(img: Image.Image) -> Image.Image:
        if img.size == (width, height):
            return img
        canvas = Image.new("L", (width, height), 255)
        canvas.paste(img, (0, 0))
        return canvas

    return pad(before), pad(after)


def stats(diff: Image.Image) -> dict[str, float | int]:
    arr = np.asarray(diff, dtype=np.uint8)
    nonzero = arr[arr > 0]
    return {
        "pixels": int(arr.size),
        "changed_pixels": int(nonzero.size),
        "changed_ratio": float(nonzero.size / arr.size),
        "mean": float(arr.mean()),
        "max": int(arr.max()),
        "p95_nonzero": float(np.percentile(nonzero, 95)) if nonzero.size else 0.0,
    }


def amplify(diff: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(diff)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--radii", default="1.5,3,6")
    args = parser.parse_args()

    before_path = resolve(args.before)
    after_path = resolve(args.after)
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    before, after = load_pair(before_path, after_path)

    report: dict[str, object] = {
        "before": str(before_path),
        "after": str(after_path),
        "radii": [],
    }

    raw = ImageChops.difference(before, after)
    raw.save(out_dir / "raw-diff.png")
    amplify(raw).save(out_dir / "raw-diff-amplified.png")
    report["raw"] = stats(raw)

    for raw_radius in args.radii.split(","):
        radius = float(raw_radius)
        b0 = before.filter(ImageFilter.GaussianBlur(radius))
        b1 = after.filter(ImageFilter.GaussianBlur(radius))
        diff = ImageChops.difference(b0, b1)
        safe_radius = str(radius).replace(".", "_")
        b0.save(out_dir / f"before-blur-r{safe_radius}.png")
        b1.save(out_dir / f"after-blur-r{safe_radius}.png")
        diff.save(out_dir / f"blur-diff-r{safe_radius}.png")
        amplify(diff).save(out_dir / f"blur-diff-r{safe_radius}-amplified.png")
        report["radii"].append({"radius": radius, **stats(diff)})

    (out_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
