# Upstream

Canonical project: <https://github.com/typeoff/martel>

Binary release source used by this toolchain: `google/fonts/ofl/martel`.

Pinned Google Fonts commit is declared in `config/martel-code.json`:

```json
"ref": "de88e79a24337aa0209f3abcc044d2500ca07021"
```

Run `make fetch` to fetch:

- `Martel-Regular.ttf`
- `Martel-DemiBold.ttf`
- `Martel-Bold.ttf`
- `OFL.txt`
- `METADATA.pb`
- `upstream_info.md`

This repo currently performs programmatic TTF metric transforms. If we later need deeper outline or source-level changes, migrate the canonical source to the upstream `.glyphs` file and build with `fontmake`/`glyphsLib`.
