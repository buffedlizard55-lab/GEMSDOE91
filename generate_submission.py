#!/usr/bin/env python3
"""DISABLED — do not use. Kept only as a fail-closed tombstone (S16, 2026-10-25).

The previous version of this file was dangerous and is the reason this stub
exists: it FABRICATED a fake `data/official/existing_faults.tif` containing a
single catalogue pixel, then emitted smoothed random noise and "validated" it
against that fake catalogue. Its output (`gems91-unique-synthetic-…-zeros.tif`)
is random noise, places 515 dots ON the real catalogue (measured this
session, `evidence/s16_forensics.json`), and must never be submitted.

Real submissions are built only by the preregistered lane scripts, e.g.:

    .venv/bin/python scripts/restore_data.py          # verify pinned inputs
    .venv/bin/python scripts/run_s16_lane.py          # build + triple-validate

which delegate encoding/certification to the shared
`scripts/submission_writer.py` (fail-closed, all-finite [0,1] zeros twin).
"""
import sys

if __name__ == "__main__":
    sys.exit(
        "generate_submission.py is disabled (it previously fabricated a fake "
        "catalogue and emitted random noise). Use scripts/run_s16_lane.py — "
        "see docs/HYPOTHESES_S16.md and docs/run-card-S16.json."
    )
