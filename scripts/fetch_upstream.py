#!/usr/bin/env python3
"""Fetch pinned upstream Martel font binaries and license metadata."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetch {url} -> {dest}")
    with urlopen(url) as response:
        dest.write_bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/martel-code.json")
    args = parser.parse_args()

    config = json.loads((ROOT / args.config).read_text())
    upstream = config["upstream"]
    ref = upstream["ref"]
    base_url = upstream["base_url"].format(ref=ref)
    out_dir = ROOT / "sources" / "upstream"

    for item in upstream["fonts"]:
        name = item["file"]
        fetch(f"{base_url}/{name}", out_dir / name)

    for name in upstream.get("docs", []):
        fetch(f"{base_url}/{name}", out_dir / name)

    lock = {
        "source": upstream["source"],
        "ref": ref,
        "base_url": base_url,
        "files": [item["file"] for item in upstream["fonts"]] + upstream.get("docs", []),
    }
    (out_dir / "UPSTREAM.lock.json").write_text(json.dumps(lock, indent=2) + "\n")


if __name__ == "__main__":
    main()
