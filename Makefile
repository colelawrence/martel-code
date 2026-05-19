.PHONY: setup fetch build proofs blur-qa kerning-scan metrics calibrate matrix cover release-fonts clean all

PY ?= .venv/bin/python
PIP ?= .venv/bin/pip
CONFIG ?= config/martel-code.json
PALETTE_CONFIG ?= config/cover-palettes.json
COVER_FONT ?= fonts/ttf/MartelCode-Regular.ttf

all: fetch build metrics proofs blur-qa kerning-scan

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

fetch:
	$(PY) scripts/fetch_upstream.py --config $(CONFIG)

build:
	$(PY) scripts/transform_font.py --config $(CONFIG)

metrics:
	$(PY) scripts/qa_metrics.py --config $(CONFIG)

proofs:
	$(PY) scripts/render_proof.py --font build/fonts/MartelCode-Regular.ttf --text proofs/text/code.txt --out build/proofs/MartelCode-Regular-code.png
	$(PY) scripts/render_proof.py --font sources/upstream/Martel-Regular.ttf --text proofs/text/code.txt --out build/proofs/Martel-Regular-code.png

blur-qa: proofs
	$(PY) scripts/blur_qa.py --before build/proofs/Martel-Regular-code.png --after build/proofs/MartelCode-Regular-code.png --out-dir build/reports/blur-code

kerning-scan:
	$(PY) scripts/kerning_blur_scan.py --font build/fonts/MartelCode-Regular.ttf --pairs proofs/text/kerning-pairs.txt --out-dir build/reports/kerning

calibrate matrix:
	$(PY) scripts/calibrate.py --config config/calibration.json

cover:
	$(PY) scripts/generate_cover.py --font $(COVER_FONT) --out assets/martel-code-cover.png --palette-config $(PALETTE_CONFIG)

release-fonts: build
	mkdir -p fonts/ttf
	cp build/fonts/MartelCode-*.ttf fonts/ttf/

clean:
	rm -rf build/fonts build/proofs build/reports
	mkdir -p build/fonts build/proofs build/reports
