# GEMSDOE91 - reproducible candidate build (merged repo layout)
# Anything that writes a raster first checks that its inputs are pinned.

PY      ?= python3
PARENT  ?= data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
SAMPLE  ?= data/official/sample_submission.tif
CAT     ?= data/official/existing_faults.tif
FEATS   ?= data/bridge/gems-geodawn-numerical-features.tif
TAG     ?= h33-h33-2-b2
FRAC    ?= 0.10
BLOCK   ?= 50
OUT     ?= releases
CAND    ?=
LEDGER  ?= ledger/submissions.csv

.PHONY: help install test preflight pins fixture demo concentration releases validate clean

help:
	@sed -n '2,10p' Makefile

install:
	$(PY) -m pip install -r requirements.txt

test:
	PYTHONPATH=.:src $(PY) -m pytest tests

# repository-wide verdict (scripts/preflight.py) and per-axis pin check
preflight:
	$(PY) scripts/preflight.py

pins:
	$(PY) -m tools.pins --axis CONCENTRATION

fixture:
	$(PY) -m tools.make_fixture --out tests/_tmp/fixture

# End-to-end proof on synthetic rasters: build, then certify with the repo gates.
# Nothing here is competition data and nothing here may be submitted.
demo: fixture
	$(PY) -m tools.run_concentration \
	  --parent tests/_tmp/fixture/parent_R0.tif \
	  --sample tests/_tmp/fixture/sample_submission.tif \
	  --catalogue tests/_tmp/fixture/catalogue_mask.tif \
	  --prior tests/_tmp/fixture/prior_kmscale.tif \
	  --parent-tag SYNTH --frac 0.15 --block-px 20 \
	  --out-dir tests/_tmp/releases --allow-unpinned
	@CAND=$$(ls tests/_tmp/releases/*.tif | grep -v zeros | head -1); \
	  $(PY) scripts/validate_release.py "$$CAND" \
	    --sample tests/_tmp/fixture/sample_submission.tif \
	    --catalogue tests/_tmp/fixture/catalogue_mask.tif \
	    --ledger ledger/submissions.csv || true
	@echo "synthetic build only - never submit tests/_tmp"

# CONCENTRATION needs the prior as a raster; derive it from training_features first
# (see docs/DATA.md and IR-91-07: never from the parent's own dots).
concentration: pins
	$(PY) -m tools.run_concentration --parent $(PARENT) --sample $(SAMPLE) \
	  --catalogue $(CAT) --prior $(PRIOR) --parent-tag $(TAG) \
	  --frac $(FRAC) --block-px $(BLOCK) --out-dir $(OUT) --register --ledger $(LEDGER)

# Rebuild every shipped release and check it against releases/MANIFEST.json.
# This is the contract CI enforces: the same pinned inputs must reproduce the same bytes.
releases: preflight
	$(PY) scripts/make_catalogue.py
	$(PY) scripts/build_spacing.py --build
	$(PY) scripts/build_relief.py --build
	$(PY) scripts/build_prune_ladder.py
	$(PY) scripts/build_prune_refill.py --build
	$(PY) scripts/build_concentration.py --build
	$(PY) scripts/build.py --axis PRUNE --value 3  --id h33-h33-2-b2-PRUNEle3norefill-20261023-1209e863  --catalogue $(CAT)
	$(PY) scripts/build.py --axis PRUNE --value 8  --id h33-h33-2-b2-PRUNEle8norefill-20261023-e1dd69d0  --catalogue $(CAT)
	$(PY) scripts/build.py --axis PRUNE --value 15 --id h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f --catalogue $(CAT)
	$(PY) scripts/update_release_manifest.py
	$(PY) scripts/update_release_manifest.py --check

validate:
	@test -n "$(CAND)" || (echo "usage: make validate CAND=releases/<id>.tif" && exit 1)
	$(PY) scripts/validate_release.py $(CAND) --sample $(SAMPLE) --catalogue $(CAT) \
	  --ledger $(LEDGER) --axis CONCENTRATION --json-out $(CAND).json

clean:
	rm -rf tests/_tmp .pytest_cache
