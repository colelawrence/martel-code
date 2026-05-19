#!/usr/bin/env python3
"""Generate a calibration matrix for Martel Code spacing decisions.

This is the orchestration layer: it owns workflow policy, while the worker scripts own
font transformation, proof rendering, blur diffs, and pair-density scanning.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def style_font_file(base_config: dict[str, Any], style: str) -> str:
    for item in base_config["upstream"]["fonts"]:
        if item["style"] == style:
            return item["file"]
    raise ValueError(f"style {style!r} is not declared in base config")


def candidate_id(tracking: float, space: float, punctuation: float) -> str:
    def fmt(value: float) -> str:
        return f"{round(value * 100):03d}"

    return f"t{fmt(tracking)}_s{fmt(space)}_p{fmt(punctuation)}"


def candidate_configs(calibration: dict[str, Any]) -> list[tuple[str, float, float, float]]:
    matrix = calibration["matrix"]
    rows = []
    for tracking, space, punctuation in itertools.product(
        matrix["tracking_em"],
        matrix["space_width_em"],
        matrix["punctuation_width_em"],
    ):
        rows.append((candidate_id(tracking, space, punctuation), float(tracking), float(space), float(punctuation)))
    return rows


def percentile_abs_z(rows: list[dict[str, Any]], percentile: float) -> float:
    values = [abs(float(row["z_score"])) for row in rows]
    return float(np.percentile(values, percentile)) if values else 0.0


def summarize_candidate(
    candidate_dir: Path,
    cid: str,
    tracking: float,
    space: float,
    punctuation: float,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    blur_report = read_json(candidate_dir / "blur" / "report.json")
    kerning_rows = read_json(candidate_dir / "kerning" / "kerning-blur-scan.json")
    worst_pairs = sorted(kerning_rows, key=lambda row: abs(float(row["z_score"])), reverse=True)[:8]
    warn_threshold = float(thresholds.get("kerning_abs_z_warn", 1.5))
    fail_threshold = float(thresholds.get("kerning_abs_z_fail", 2.0))
    warn_count = sum(1 for row in kerning_rows if abs(float(row["z_score"])) >= warn_threshold)
    fail_count = sum(1 for row in kerning_rows if abs(float(row["z_score"])) >= fail_threshold)
    decision = "fail" if fail_count else "manual-review" if warn_count else "candidate"
    return {
        "id": cid,
        "tracking_em": tracking,
        "space_width_em": space,
        "punctuation_width_em": punctuation,
        "font": str((candidate_dir / "fonts" / "MartelCode-Regular.ttf").relative_to(ROOT)),
        "proof": str((candidate_dir / "proof.png").relative_to(ROOT)),
        "contact_proof": str((candidate_dir / "contact-proof.png").relative_to(ROOT)),
        "raw_changed_ratio": blur_report["raw"]["changed_ratio"],
        "blur_mean_by_radius": {str(row["radius"]): row["mean"] for row in blur_report["radii"]},
        "kerning_max_abs_z": max((abs(float(row["z_score"])) for row in kerning_rows), default=0.0),
        "kerning_p95_abs_z": percentile_abs_z(kerning_rows, 95),
        "kerning_warn_count": warn_count,
        "kerning_fail_count": fail_count,
        "decision": decision,
        "worst_pairs": [
            {"pair": row["pair"], "z_score": row["z_score"], "boundary_density": row["boundary_density"]}
            for row in worst_pairs
        ],
    }


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "tracking_em",
        "space_width_em",
        "punctuation_width_em",
        "raw_changed_ratio",
        "kerning_max_abs_z",
        "kerning_p95_abs_z",
        "kerning_warn_count",
        "kerning_fail_count",
        "decision",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})


def make_contact_sheet(rows: list[dict[str, Any]], out_path: Path, columns: int = 1, thumb_width: int = 2200) -> None:
    if not rows:
        return
    label_height = 56
    thumbs: list[tuple[dict[str, Any], Image.Image]] = []
    for row in rows:
        img = Image.open(ROOT / row.get("contact_proof", row["proof"])).convert("L")
        scale = thumb_width / img.width
        thumb = img.resize((thumb_width, max(1, round(img.height * scale))))
        thumbs.append((row, thumb))

    cell_width = thumb_width
    cell_height = max(thumb.height for _row, thumb in thumbs) + label_height
    sheet_width = columns * cell_width
    sheet_height = ((len(thumbs) + columns - 1) // columns) * cell_height
    sheet = Image.new("L", (sheet_width, sheet_height), 255)
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for index, (row, thumb) in enumerate(thumbs):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        label = f"{row['id']}  track={row['tracking_em']:.2f} space={row['space_width_em']:.2f} punct={row['punctuation_width_em']:.2f}"
        label2 = f"{row['decision']}  kern max|z|={row['kerning_max_abs_z']:.2f}  p95={row['kerning_p95_abs_z']:.2f}"
        draw.text((x + 8, y + 6), label, fill=0, font=font)
        draw.text((x + 8, y + 24), label2, fill=0, font=font)
        sheet.paste(thumb, (x, y + label_height))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/calibration.json")
    parser.add_argument("--out-dir", default="build/calibration")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N candidates for quick smoke checks")
    args = parser.parse_args()

    calibration_path = resolve(args.config)
    calibration = read_json(calibration_path)
    base_config_path = resolve(calibration["base_config"])
    base_config = read_json(base_config_path)
    style = calibration["style"]
    out_dir = resolve(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    proof_text = resolve(calibration["proof_text"])
    contact_text = resolve(calibration.get("contact_text", calibration["proof_text"]))
    pairs = resolve(calibration["kerning_pairs"])
    upstream_font = ROOT / "sources" / "upstream" / style_font_file(base_config, style)
    if not upstream_font.exists():
        raise FileNotFoundError(f"Missing {upstream_font}; run `make fetch` first")

    render = calibration["render"]
    contact_render = calibration.get("contact_render", render)
    contact_sheet = calibration.get("contact_sheet", {})
    radii = ",".join(str(radius) for radius in calibration["blur"]["radii"])

    upstream_proof = out_dir / "upstream" / "proof.png"
    run([
        sys.executable,
        "scripts/render_proof.py",
        "--font",
        str(upstream_font.relative_to(ROOT)),
        "--text",
        str(proof_text.relative_to(ROOT)),
        "--out",
        str(upstream_proof.relative_to(ROOT)),
        "--size",
        str(render["size"]),
        "--width",
        str(render["width"]),
        "--line-height",
        str(render["line_height"]),
        "--margin",
        str(render["margin"]),
    ])

    summaries: list[dict[str, Any]] = []
    candidates = candidate_configs(calibration)
    thresholds = calibration.get("thresholds", {})
    if args.limit is not None:
        candidates = candidates[: args.limit]

    for cid, tracking, space, punctuation in candidates:
        candidate_dir = out_dir / cid
        candidate_config = json.loads(json.dumps(base_config))
        candidate_config["spacing"]["tracking_em"] = tracking
        candidate_config["spacing"]["space_width_em"] = space
        candidate_config["punctuation"]["normalized_width_em"] = punctuation
        config_path = candidate_dir / "config.json"
        write_json(config_path, candidate_config)

        run([
            sys.executable,
            "scripts/transform_font.py",
            "--config",
            str(config_path.relative_to(ROOT)),
            "--out-font-dir",
            str((candidate_dir / "fonts").relative_to(ROOT)),
            "--report-dir",
            str((candidate_dir / "reports").relative_to(ROOT)),
            "--styles",
            style,
        ])

        font_path = candidate_dir / "fonts" / f"{base_config['family_name'].replace(' ', '')}-{style.replace(' ', '')}.ttf"
        proof_path = candidate_dir / "proof.png"
        run([
            sys.executable,
            "scripts/render_proof.py",
            "--font",
            str(font_path.relative_to(ROOT)),
            "--text",
            str(proof_text.relative_to(ROOT)),
            "--out",
            str(proof_path.relative_to(ROOT)),
            "--size",
            str(render["size"]),
            "--width",
            str(render["width"]),
            "--line-height",
            str(render["line_height"]),
            "--margin",
            str(render["margin"]),
        ])

        contact_proof_path = candidate_dir / "contact-proof.png"
        run([
            sys.executable,
            "scripts/render_proof.py",
            "--font",
            str(font_path.relative_to(ROOT)),
            "--text",
            str(contact_text.relative_to(ROOT)),
            "--out",
            str(contact_proof_path.relative_to(ROOT)),
            "--size",
            str(contact_render["size"]),
            "--width",
            str(contact_render["width"]),
            "--line-height",
            str(contact_render["line_height"]),
            "--margin",
            str(contact_render["margin"]),
        ])

        run([
            sys.executable,
            "scripts/blur_qa.py",
            "--before",
            str(upstream_proof.relative_to(ROOT)),
            "--after",
            str(proof_path.relative_to(ROOT)),
            "--out-dir",
            str((candidate_dir / "blur").relative_to(ROOT)),
            "--radii",
            radii,
        ])

        run([
            sys.executable,
            "scripts/kerning_blur_scan.py",
            "--font",
            str(font_path.relative_to(ROOT)),
            "--pairs",
            str(pairs.relative_to(ROOT)),
            "--out-dir",
            str((candidate_dir / "kerning").relative_to(ROOT)),
        ])
        summaries.append(summarize_candidate(candidate_dir, cid, tracking, space, punctuation, thresholds))

    reference = calibration.get("reference_candidate")
    reference_id = candidate_id(reference["tracking_em"], reference["space_width_em"], reference["punctuation_width_em"]) if reference else None
    reference_row = next((row for row in summaries if row["id"] == reference_id), None)
    if reference_row:
        for row in summaries:
            row["delta_from_reference"] = {
                "raw_changed_ratio": row["raw_changed_ratio"] - reference_row["raw_changed_ratio"],
                "kerning_max_abs_z": row["kerning_max_abs_z"] - reference_row["kerning_max_abs_z"],
                "kerning_p95_abs_z": row["kerning_p95_abs_z"] - reference_row["kerning_p95_abs_z"],
            }

    summary = {
        "config": str(calibration_path.relative_to(ROOT)),
        "base_config": str(base_config_path.relative_to(ROOT)),
        "style": style,
        "candidate_count": len(summaries),
        "reference_candidate_id": reference_id,
        "thresholds": thresholds,
        "candidates": summaries,
    }
    write_json(out_dir / "summary.json", summary)
    write_summary_csv(out_dir / "summary.csv", summaries)
    make_contact_sheet(
        summaries,
        out_dir / "contact-sheet.png",
        columns=int(contact_sheet.get("columns", 1)),
        thumb_width=int(contact_sheet.get("thumb_width", 2200)),
    )
    print(f"wrote {out_dir / 'summary.json'}")
    print(f"wrote {out_dir / 'summary.csv'}")
    print(f"wrote {out_dir / 'contact-sheet.png'}")


if __name__ == "__main__":
    main()
