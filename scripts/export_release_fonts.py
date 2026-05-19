#!/usr/bin/env python3
"""Export release-ready Martel Code font formats.

Outputs:
- fonts/ttf: installable TrueType fonts
- fonts/otf: OpenType sfnt fonts with TrueType outlines
- fonts/woff2: compressed web fonts
- dist/*.zip: easy-download release archives
"""
from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()


def save_woff2(source: Path, dest: Path) -> None:
    font = TTFont(source, recalcTimestamp=False)
    font.flavor = "woff2"
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.save(dest, reorderTables=False)


def save_otf(source: Path, dest: Path) -> None:
    # These are OpenType sfnt fonts with TrueType outlines. The extension is
    # provided for users/tools that ask for OpenType packages; outlines remain
    # glyf/quadratic, not CFF/PostScript.
    font = TTFont(source, recalcTimestamp=False)
    dest.parent.mkdir(parents=True, exist_ok=True)
    font.save(dest, reorderTables=False)


def zip_dir(source_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source_dir.glob("*")):
            if path.is_file():
                archive.write(path, arcname=f"{source_dir.name}/{path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="build/fonts")
    parser.add_argument("--fonts-dir", default="fonts")
    parser.add_argument("--dist-dir", default="dist")
    args = parser.parse_args()

    source_dir = resolve(args.source_dir)
    fonts_dir = resolve(args.fonts_dir)
    dist_dir = resolve(args.dist_dir)
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing {source_dir}; run `make build` first")

    ttf_dir = fonts_dir / "ttf"
    otf_dir = fonts_dir / "otf"
    woff2_dir = fonts_dir / "woff2"
    clean_dir(ttf_dir)
    clean_dir(otf_dir)
    clean_dir(woff2_dir)
    clean_dir(dist_dir)

    ttf_paths = sorted(source_dir.glob("MartelCode-*.ttf"))
    if not ttf_paths:
        raise FileNotFoundError(f"No MartelCode-*.ttf files found in {source_dir}")

    for source in ttf_paths:
        ttf_dest = ttf_dir / source.name
        shutil.copy2(source, ttf_dest)
        save_otf(ttf_dest, otf_dir / source.with_suffix(".otf").name)
        save_woff2(ttf_dest, woff2_dir / source.with_suffix(".woff2").name)

    zip_dir(ttf_dir, dist_dir / "martel-code-ttf.zip")
    zip_dir(otf_dir, dist_dir / "martel-code-otf.zip")
    zip_dir(woff2_dir, dist_dir / "martel-code-woff2.zip")

    all_zip = dist_dir / "martel-code-fonts.zip"
    with zipfile.ZipFile(all_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for directory in (ttf_dir, otf_dir, woff2_dir):
            for path in sorted(directory.glob("*")):
                if path.is_file():
                    archive.write(path, arcname=f"{directory.name}/{path.name}")

    for path in sorted(ttf_dir.glob("*")) + sorted(otf_dir.glob("*")) + sorted(woff2_dir.glob("*")) + sorted(dist_dir.glob("*")):
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
