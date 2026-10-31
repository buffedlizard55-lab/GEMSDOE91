#!/usr/bin/env python3
"""Validate the S30-VCSE review evidence, then let the single-owner front door
stamp the public pages from the canonical sources in ``docs/s30-vcse/pages/``.

Runs inside ``scripts.render_review_20261030.render()`` after
``front_door.enforce()``.  Consumes only committed evidence and fails closed:
if the run card, receipt, verdict, or uniqueness gates disagree, the render
raises and tests fail.  Never grants permission to submit; never uploads.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
RUN_CARD = ROOT / "docs/s30-vcse/run-card.json"
RECEIPT = ROOT / ("docs/downloads/gems91-s30-vcse-e3-44090dots-"
                  "20261031T021738Z-d23f1602-zeros.json")
EXPECT_NAME = "gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros"
EXPECT_SHA = "a5993d3a520aa280ce70744ad2dd772090d54cd248e1d6fdc9d1950fdc8e83ae"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_inputs(root: Path = ROOT) -> tuple[dict, dict]:
    card = _read_json(RUN_CARD)
    receipt = _read_json(RECEIPT)
    if card.get("verdict") != "negative":
        raise ValueError("S30 run card must remain negative until the holdout gate passes")
    if card.get("submission", {}).get("name") != EXPECT_NAME:
        raise ValueError("Submission name drift")
    if card.get("raster_sha256") != EXPECT_SHA or receipt.get("sha256") != EXPECT_SHA:
        raise ValueError("Candidate raster digest drift")
    if not receipt.get("validator", {}).get("all_checks_passed"):
        raise ValueError("Validator receipt is not a pass")
    note = card.get("submission", {}).get("note", "")
    if not (0 < len(note) <= 140):
        raise ValueError("Submission note must fit the 140-char limit")
    hg = card.get("holdout_gate", {})
    if hg.get("pass") is not False or card.get("g5_blind_sgmc_pass") is not True:
        raise ValueError("Verdict inputs drifted; keep G5 pass + holdout fail visible")
    uniq = card.get("registry_uniqueness", {})
    max_ov = float(uniq.get("dot_max_overlap_within_3px", 1.0))
    if max_ov > 0.70:
        raise ValueError("Duplicate stop: dot overlap above 70%")
    return card, receipt


def render(root: Path = ROOT) -> None:
    card, receipt = validate_inputs(root)
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import front_door as _fd  # noqa: PLC0415
    if not _fd.enforce():
        raise ValueError("front door did not stamp the S30-VCSE active pages")


if __name__ == "__main__":
    render()
