# GEMSDOE91 — reproducible candidate build
# Every target that writes a raster first runs preflight; nothing is built unpinned.

PY      ?= python3
PARENT  ?= data/h33-h33-2-b2.tif
SAMPLE  ?= data/sample_submission.tif
CAT     ?= data/catalogue_mask.tif
PRIOR   ?= data/prior_kmscale.tif
TAG     ?= R0
FRAC    ?= 0.10
BLOCK   ?= 50
OUT     ?= releases
CAND    ?=

.PHONY: help install test preflight fixture demo concentration validate clean

help:
	@sed -n '2,12p' Makefile

install:
	$(PY) -m pip install -r requirements.txt

test:
	PYTHONPATH=. $(PY) -m pytest tests -q

preflight:
	$(PY) -m tools.preflight --axis ALL

fixture:
	$(PY) -m tools.make_fixture --out tests/_tmp/fixture

# end-to-end proof on synthetic rasters: build, then gate the result
demo: fixture
	$(PY) -m tools.run_concentration --parent tests/_tmp/fixture/parent_R0.tif \
	  --sample tests/_tmp/fixture/sample_submission.tif \
	  --catalogue tests/_tmp/fixture/catalogue_mask.tif \
	  --prior tests/_tmp/fixture/prior_kmscale.tif \
	  --parent-tag SYNTH --frac 0.15 --block-px 20 --out-dir tests/_tmp/releases --allow-unpinned
	@echo "synthetic build only - never submit tests/_tmp"

concentration: preflight
	$(PY) -m tools.run_concentration --parent $(PARENT) --sample $(SAMPLE) \
	  --catalogue $(CAT) --prior $(PRIOR) --parent-tag $(TAG) \
	  --frac $(FRAC) --block-px $(BLOCK) --out-dir $(OUT)

validate:
	@test -n "$(CAND)" || (echo "usage: make validate CAND=releases/<id>.tif" && exit 1)
	$(PY) -m tools.validate_submission --candidate $(CAND) --sample $(SAMPLE) \
	  --catalogue $(CAT) --ledger ledger/submissions.csv --parent $(PARENT) \
	  --json releases/$(notdir $(basename $(CAND)))-receipt.json

clean:
	rm -rf tests/_tmp .pytest_cache
