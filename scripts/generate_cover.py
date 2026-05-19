#!/usr/bin/env python3
"""Generate the README cover image using Martel Code and Phosphor themes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CODE_SAMPLE = [
    [("comment", "// soft, readable, precise")],
    [
        ("keyword", "const"),
        ("plain", " mood "),
        ("operator", "="),
        ("plain", " "),
        ("function", "MartelCode"),
        ("punctuation", "({"),
    ],
    [("plain", "  tracking"), ("punctuation", ":"), ("number", " 0.05"), ("punctuation", ",")],
    [("plain", "  nums"), ("punctuation", ":"), ("string", " \"1.00 12.0 123.\""), ("punctuation", ",")],
    [("plain", "  zero"), ("punctuation", ":"), ("string", " \"0 00 0O0O\""), ("punctuation", ",")],
    [("punctuation", "});")],
]


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def strip_line_comments_from_jsonc(text: str) -> str:
    output: list[str] = []
    in_string = False
    escaping = False
    index = 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if char == '"' and not escaping:
            in_string = not in_string
        if not in_string and char == "/" and next_char == "/":
            while index < len(text) and text[index] != "\n":
                index += 1
            output.append("\n")
            escaping = False
            continue
        output.append(char)
        escaping = in_string and char == "\\" and not escaping
        if char != "\\":
            escaping = False
        index += 1
    return "".join(output)


def load_theme(path: Path) -> dict[str, Any]:
    return json.loads(strip_line_comments_from_jsonc(path.read_text()))


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 8:
        value = value[:6]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3))


def token_rule(theme: dict[str, Any], scope: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for rule in theme.get("tokenColors", []):
        scopes = rule.get("scope")
        if isinstance(scopes, str):
            parts = [part.strip() for part in scopes.split(",")]
        elif isinstance(scopes, list):
            parts = scopes
        else:
            parts = []
        if scope in parts:
            found = rule.get("settings", {})
    return found


def cover_palette(raw: dict[str, str]) -> dict[str, tuple[int, int, int]]:
    return {key: hex_to_rgb(value) for key, value in raw.items()}


def theme_palette(theme: dict[str, Any]) -> dict[str, tuple[int, int, int]]:
    colors = theme["colors"]

    def color(kind: str, scope: str | None, fallback: str) -> tuple[int, int, int]:
        if scope is not None:
            value = token_rule(theme, scope).get("foreground")
            if value:
                return hex_to_rgb(value)
        return hex_to_rgb(fallback)

    return {
        "background": hex_to_rgb(colors.get("editor.background", "#ffffff")),
        "foreground": hex_to_rgb(colors.get("editor.foreground", colors.get("foreground", "#000000"))),
        "line": hex_to_rgb(colors.get("editorLineNumber.foreground", "#999999")),
        "selection": hex_to_rgb(colors.get("editor.selectionBackground", "#99999933")),
        "tab": hex_to_rgb(colors.get("tab.activeBackground", colors.get("editorGroupHeader.tabsBackground", colors.get("editor.background", "#ffffff")))),
        "border": hex_to_rgb(colors.get("editorWidget.border", colors.get("sideBar.border", "#999999"))),
        "keyword": color("keyword", "keyword", colors.get("editor.foreground", "#000000")),
        "number": color("number", "constant.numeric", colors.get("editor.foreground", "#000000")),
        "string": color("string", "string", colors.get("editor.foreground", "#000000")),
        "function": color("function", "entity.name.function", colors.get("editor.foreground", "#000000")),
        "comment": color("comment", "comment", colors.get("descriptionForeground", "#777777")),
        "operator": color("operator", "keyword.operator", colors.get("editor.foreground", "#000000")),
        "punctuation": color("punctuation", "punctuation", colors.get("editor.foreground", "#000000")),
        "plain": hex_to_rgb(colors.get("editor.foreground", colors.get("foreground", "#000000"))),
    }


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def draw_code_sample(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    palette: dict[str, tuple[int, int, int]],
    code_font: ImageFont.FreeTypeFont,
) -> None:
    x, y = xy
    gutter_x = x
    code_x = x + 68
    line_gap = 58
    for line_no, segments in enumerate(CODE_SAMPLE, start=1):
        yy = y + (line_no - 1) * line_gap
        draw.text((gutter_x, yy), str(line_no).rjust(2), font=code_font, fill=palette["line"])
        xx = code_x
        for kind, text in segments:
            draw.text((xx, yy), text, font=code_font, fill=palette.get(kind, palette["plain"]))
            xx += round(draw.textlength(text, font=code_font))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--font", default="build/fonts/MartelCode-Regular.ttf")
    parser.add_argument("--out", default="assets/martel-code-cover.png")
    parser.add_argument("--palette-config", default="config/cover-palettes.json")
    parser.add_argument("--slime-theme", default=None)
    parser.add_argument("--tokyo-light-theme", default=None)
    parser.add_argument("--width", type=int, default=1800)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    font_path = resolve(args.font)
    if not font_path.exists():
        raise FileNotFoundError(f"Missing {font_path}; run `make build` first")

    if args.slime_theme is not None or args.tokyo_light_theme is not None:
        if args.slime_theme is None or args.tokyo_light_theme is None:
            raise ValueError("Pass both --slime-theme and --tokyo-light-theme, or neither")
        slime_theme = resolve(args.slime_theme)
        tokyo_light_theme = resolve(args.tokyo_light_theme)
        if not slime_theme.exists():
            raise FileNotFoundError(f"Missing Slime theme: {slime_theme}")
        if not tokyo_light_theme.exists():
            raise FileNotFoundError(f"Missing Tokyo Night Light theme: {tokyo_light_theme}")
        slime = theme_palette(load_theme(slime_theme))
        tokyo = theme_palette(load_theme(tokyo_light_theme))
    else:
        palette_config = resolve(args.palette_config)
        if not palette_config.exists():
            raise FileNotFoundError(f"Missing palette config: {palette_config}")
        palettes = json.loads(palette_config.read_text())
        slime = cover_palette(palettes["slime"])
        tokyo = cover_palette(palettes["tokyoLight"])
    width = args.width
    height = args.height
    half_width = width // 2
    image = Image.new("RGB", (width, height), tokyo["background"])
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, half_width, height), fill=tokyo["background"])
    draw.rectangle((half_width, 0, width, height), fill=slime["background"])

    code_font = font(font_path, 44)
    top = 250
    rail_margin = 54
    draw_code_sample(draw, (rail_margin, top), tokyo, code_font)
    draw_code_sample(draw, (half_width + rail_margin, top), slime, code_font)

    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
