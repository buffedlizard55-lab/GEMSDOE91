# S91-ALM three-pass review — 2026-10-31

**Branch:** `arena/2664739c-gemsdoe91` · **Lane:** `S91-ALM` · **Verdict:** unique candidate generated, format-certified; **OK TO DOWNLOAD: YES · OK TO SUBMIT: NO** (negative holdout, selector step pending).

## Executive decision

| Question | Finding |
|---|---|
| New unique TIFF created? | **YES** — `gems91-s91-alm-alteration-halo-20261031T010114Z-5834ff6c-zeros.tif` |
| OK to download a new candidate? | **YES** — direct GeoTIFF + single-TIFF ZIP published under `docs/downloads/` |
| OK to submit? | **NO** — HOLDOUT-DTI 0.0 by design; blind SGMC control below parent R0; no organizer receipt; selector step pending |
| HOLDOUT-DTI measured? | **0.0 [0.0, 0.0]**, `gems91-hide-recover-v1.1-nohalo`, 60,988 withheld positives (negative by design) |
| Blind SGMC off-catalogue control? | **0.062396** (62,122 off-catalogue positives) vs parent R0 **0.095386** |
| ORGANIZER-CONFIRMED score? | **None** |
| Leaderboard score estimate? | **None** — no projection is written as a score |
| Experiments / slots used? | **1 / 0** |

## Pass 1 — repository shape and request coverage

- The 15 pinned manifest inputs were **absent** at session start; `scripts/restore_data.py` re-fetched all 15 from the
  verified `buffedlizard55-lab/60GEMSDOE` mirror and re-hashed every byte against `registry/data_manifest.json`
  (all 15 OK). `scripts/preflight.py` now reports **INPUTS AVAILABLE**, all six build axes READY.
- The nine focus-site leaders were downloaded from their pinned commits via `codeload.github.com` and SHA-256 re-checked
  (all nine match `docs/review-20261030/nine-site-snapshot.json`).
- A new method lane (`S91-ALM`) was implemented in `scripts/build_s91_alm.py`, reusing the **shared**
  `scripts/submission_writer.py` (no private fork of format rules).

## Pass 2 — executable checks and failure modes

| Check | Result |
|---|---|
| `scripts/restore_data.py` | 15/15 pinned inputs verified |
| `scripts/preflight.py` | INPUTS AVAILABLE, 6/6 axes READY |
| `scripts/build_s91_alm.py` | built 37,654 dots, `gems91.gates` **CERTIFIED** |
| `gems91.gates` / `release_gates` / `validate_raster` | all PASS (nan + zeros encodings) |
| Uniqueness vs nine leaders | max **23.83%** 3-px overlap (GEMSDOE27) — **unique** |
| Uniqueness vs all local rasters | max **33.75%** — **unique** |
| HOLDOUT-DTI | **0.0** (collar-compliant by design) |
| Blind SGMC off-catalogue control | **0.062396** vs R0 **0.095386** |

Two bugs were found and fixed during the build: a rank-assignment shape mismatch in `robust_rank01`, and a
`stem_prefix`/bundle-filename collision in the shared writer (now per-run unique). The stale
`tests/test_active_review_8f9cff19.py::test_preflight_snapshot_matches_missing_required_inputs` assertion was updated
to reflect the restored inputs (see Pass 3).

## Pass 3 — request-to-repo consistency

- **Unique competition TIFF:** generated, format-certified, and verified unique against all nine leaders and every
  locally available registry raster.
- **High-score gate:** the candidate is a **negative holdout result by design**. It is unique and safe to download, but
  it does **not** beat the supplied 0.2778 claim and no leaderboard estimate is asserted.
- **Uniqueness:** pre-placement and final-dot checks both pass (max 23.83% vs the nine; max 33.75% vs all local rasters;
  threshold 70%).
- **No human inspection:** every gate is automated; no manual input was used.
- **Hypotheses:** see `HYPOTHESES.md` — three new, ranked, untested proposals are recorded for the next session.

## Blockers and next actions

1. The alteration-halo lane is unique but under-performs the parent R0 on the blind SGMC control. The next session
   should implement the ranked hypothesis #1 (radiometric-alteration × magnetic-low × gravity-gradient discordance with
   submodular emission) and re-measure.
2. A full-registry uniqueness pass (all 211 frozen rasters) requires the fleet registry bytes; only the nine leaders and
   local rasters were available here.
3. No organizer receipt exists; any real submission must be recorded as ORGANIZER-CONFIRMED from the submission page.

**Maximize P(Win) · Own the Outcome.**
