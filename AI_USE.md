# AI_USE — disclosure required by the competition rules

Rules reference: `https://docs.nlr.gov/docs/fy26osti/96647.pdf` (generative-AI disclosure).
This file separates what the AI *wrote* from what the **human decided**. Update it at
every session; do not let the AI write the "human decided" column.

## Session 2026-10-23 — agent (`arena/a6416f7b-gemsdoe91`)

### Written by the AI

- `tools/dti.py` — DTI algebra, triangular kernel, credit map, exact marginal-gain
  ranking, greedy selector, plus the unit tests that pin the algebra's assumptions.
- `tools/validate_submission.py` — all MUST gates, the report-only proxy and
  leakage-canary machinery.
- `tools/run_concentration.py` — the CONCENTRATION axis builder and its mechanism card.
- `tools/preflight.py`, `tools/stor.py`, `tools/raster_io.py`, `tools/make_fixture.py`.
- `tests/` (49 tests, all on synthetic rasters).
- `SLOT_PLAN.md`, `IRREGULARITIES.md`, `docs/*`, `registry/data_manifest.json` (all
  hashes `null`), `Makefile`, `.github/workflows/ci.yml`, `.gitignore`.
- Session axis choice: **CONCENTRATION** (brief §1 delegates this to the agent when
  the human does not assign one).

### Decided by the human (fill in; blank = not decided)

| decision | human's answer |
|---|---|
| TOP_PUBLIC (number + date read from the leaderboard) | |
| Slots remaining this week / total | |
| Deadline confirmed on the competition page (y/n) | |
| Which reading of the catalogue buffer is the real gate (I-3) | |
| Whether the official metric treats `|G|` as constant (I-5) | |
| Where the parent raster + its ranking come from (I-1, I-4) | |
| Which file to submit, and the submission-window day | |
| Accept/override the agent's axis choice | |

### What the AI did NOT do

- Did not read, scrape, log into or submit anything on the competition site.
- Did not fabricate a parent raster, a score, a receipt, a licence or an external dataset.
- Did not contact dropbox.com or any non-allowlisted host.
- Did not claim any number as a score: every figure produced is labelled MODEL or PROXY.
- Did not build a variant. No raster left `releases/`.
