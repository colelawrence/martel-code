.PHONY: setup fetch build italics proofs blur-qa kerning-scan metrics variable-audit calibrate matrix cover release-fonts clean all

PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
CONFIG ?= config/martel-code.json
PALETTE_CONFIG ?= config/cover-palettes.json
COVER_FONT ?= fonts/ttf/MartelCode-Regular.ttf
COVER_ITALIC_FONT ?= fonts/ttf/MartelCode-Italic.ttf

all: fetch build metrics proofs blur-qa kerning-scan

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

fetch:
	$(PY) scripts/fetch_upstream.py --config $(CONFIG)

build:
	$(PY) scripts/transform_font.py --config $(CONFIG)

italics: build
	$(PY) scripts/generate_italic_fonts.py --source-dir build/fonts --out-dir build/fonts

metrics:
	$(PY) scripts/qa_metrics.py --config $(CONFIG)

proofs:
	$(PY) scripts/render_proof.py --font build/fonts/MartelCode-Regular.ttf --text proofs/text/code.txt --out build/proofs/MartelCode-Regular-code.png
	$(PY) scripts/render_proof.py --font sources/upstream/Martel-Regular.ttf --text proofs/text/code.txt --out build/proofs/Martel-Regular-code.png

blur-qa: proofs
	$(PY) scripts/blur_qa.py --before build/proofs/Martel-Regular-code.png --after build/proofs/MartelCode-Regular-code.png --out-dir build/reports/blur-code

kerning-scan:
	$(PY) scripts/kerning_blur_scan.py --font build/fonts/MartelCode-Regular.ttf --pairs proofs/text/kerning-pairs.txt --out-dir build/reports/kerning

variable-audit: release-fonts
	$(PY) scripts/audit_variable_compatibility.py --out build/reports/variable-compatibility.json

calibrate matrix:
	$(PY) scripts/calibrate.py --config config/calibration.json

cover:
	$(PY) scripts/generate_cover.py --font $(COVER_FONT) --italic-font $(COVER_ITALIC_FONT) --out assets/martel-code-cover.png --palette-config $(PALETTE_CONFIG)

release-fonts: italics
	$(PY) scripts/export_release_fonts.py --source-dir build/fonts --fonts-dir fonts --dist-dir dist

clean:
	rm -rf build/fonts build/proofs build/reports
	mkdir -p build/fonts build/proofs build/reports
