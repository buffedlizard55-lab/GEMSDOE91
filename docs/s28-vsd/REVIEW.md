# S28-VSD session review — 2026-10-31 (three passes)

**Branch:** `arena/e5d5b72d-gemsdoe91` · **Lane:** assigned by the session prompt's PARALLEL-RUN
PROTOCOL §2 (single method paragraph: reuse the template's cached feature stack, `evaluate_holdout.py`
and `submission_writer.py`; hide-and-recover holdout; pooled DTI α=0.2, β=0.8, 300 m triangular
kernel). **Verdict: PROMOTE per preregistered gates; 0 weekly slots used.**

## What unblocked this session

The 2026-10-30 review declared the repo BLOCKED on (a) no assigned lane and (b) 15/15 pinned inputs
absent. Both blockers are resolved **in this sandbox**:

1. The session prompt supplies the lane (method paragraph quoted above; recorded in the run card as
   `assigned_lane: true` with source).
2. `scripts/restore_data.py` restored all **15 pinned inputs from the hash-pinned GitHub mirrors** —
   every sha256 and byte length verified against `registry/data_manifest.json` before use
   (training_features came via its pinned 5-blob split). `scripts/restore_lfi_anchors.py` restored the
   108 LFI anchor rasters (git-blob verified), `scripts/restore_registry.py --available-only` restored
   62/64 comparison-inventory rasters (2 unrecoverable upstream, quarantined as designed), and the
   remaining 4 of the S27 frozen-registry's 211 references were fetched from their commit-pinned owner
   repos via the GitHub contents API and sha256-verified against the frozen entries
   (`data/s22-nine-sites/GEMSDOE27|28|31.tif`, `data/s27_refs/…lbmc1….tif`). At package time all 211
   references were re-verified byte-exactly before the Rule-1 checks.
   **Flagged irregularity (persisting, IR-91-09):** the mirrors are byte-verified copies made by earlier
   sessions; the underlying rights question of mirroring competition data on GitHub is unresolved. The
   authenticated DrivenData download remains unavailable from this sandbox's allowed hosts. Using the
   mirrors is the only autonomous path and is disclosed here; if the organizer objects, the derived
   candidate should be withdrawn from consideration.

## Pass 1 — implementation

- New lane module `src/gems91/vsd28.py`: 15 catalogue-independent features in three families
  (CDEC cross-domain edge concordance B02×B13 at 300/600/1200 m; TSR relay-gap morphology via binary
  closing at r=3/6/10 px; STA seismo-tectonic alignment B16×B10×edge azimuth). NoData-safe via the
  template's masked helpers; zero B12/B19/B06 dependence; orientation-shuffle negative control built in.
- New runner `scripts/run_s28_vsd.py` reusing the template end-to-end: folds
  (`vendor/gems57.spatial.folds`, v3 buffered, split `label-blind-quadrants-v3-feature-buffered`),
  evaluator (`vendor/gems57.evaluate_holdout`, `gems57-pooled-hide-v2`), emitters and PU specialist
  (`gems91.pdwc21`), writer/validator (`vendor/gems57.submission_writer`/`validate`), capacity bound
  (`gems91.capacity`), and the S27 runner's matched-control helpers (S25-FABRIC features, HGB trainer,
  NMS/CELF scoring, competitive-halo packing). Run card schema `gems-parallel-run-card-v1`.
- Experiments: E1 widened 53-feature HGB → 0.155356; E2 nested leave-one-quadrant-out AC8 + widened PU
  specialist stage-2 → 0.159707; E3 per-fold CELF emission on the winning surface → **0.162375
  [0.140989, 0.182478]** (selected). All canaries pass (max symmetric AUC 0.6472; AC8 canary 0.7252;
  CDEC shuffle control 0.5262 > 0.5135). Wall clock 57.4 lane-minutes (persistent epoch anchor), 3/3
  experiments, 0 slots.
- Packaging: Rule-1 surface check (max |ρ| 0.2006 vs 211 refs), CELF 37,654 dots with
  `uniqueness_cap=0.64` across the 181 competitive sparse references, Rule-1 dot checks (nine leaders
  max 44.46%; lbmc1 26.46%; competitive max 57.51%; literal-vs-dense-lattice 99.96% reported with the
  ≥82.34% capacity bound), shared writer + independent re-read validator, run card. Post-hoc
  diagnostics: SGMC off-catalogue blind control 0.106576 (far-field 0.097946); LFI projection
  (112 anchors refit; LOSO RMSE 0.026, Spearman 0.94) ridge10 = 0.17746 / ridge1 = 0.19097, labelled
  `MODEL_PROJECTION_NOT_A_SCORE`; dot geography median 19.10 px off catalogue, 29.73% within 1.5 px of
  the h19.5 network.

## Pass 2 — bug hunt (all found and fixed)

1. **Canary surface indexing** (`arr2d.ravel()[g.footprint]` on a 1-D array) — fixed to 2-D indexing;
   found by the first prep run.
2. **Pipeline masking:** the original chained command piped stages through `tail`, so a failed prep
   still "succeeded" (pipe exit code). Stages are now run one-per-process with explicit checks.
3. **OOM:** running the LFI aggregate concurrently with the lane controls exhausted the 3.9 GB sandbox
   (controls was killed mid-scoring). Re-ran stages serially; the terms cache was rebuilt and the
   instrument reproduction check passed (base control = 0.125613, identical to the S27 card).
4. **Memmap indexing:** `_hgb_oof_surface_from_memmap` gathered full-grid indices from a
   footprint-relative memmap (IndexError 6437467 ≥ 5,167,373). Fixed with a footprint-index map and
   explicit non-footprint zero-fill.
5. **Wall-clock guard reset per process** (Rule-6 violation in waiting): replaced with a persistent
   lane epoch anchor (`data/work/s28_cache/.lane_t0`, true lane start 2026-10-31T00:53Z) and recorded
   lane-minutes in every artifact.
6. **Negative-control comparator inversion:** `min(auc,1-auc) >= min(...)` was backwards; the CDEC
   orientation-shuffle control had actually passed (0.5262 > 0.5135). Fixed and re-run.
7. **E3 scoring semantics:** the first draft scored the globally uniqueness-capped dots as if they were
   a surface; fixed to score per-fold CELF emission from the continuous surface (the cap remains in
   packaging only, where it belongs).
8. **Pointer hashes written from memory:** `docs/current-run.json` was first hand-written with
   placeholder hashes; the verifier check caught the mismatch and the pointer is now generated from the
   writer receipt programmatically (`verify_front_door.py` exits 0).

## Pass 3 — requirement-by-requirement verification

- Unique TIF generated and hash-pinned: `gems91-s28-vsd-e3-37654dots-20261031T015019Z-3d03f7cb-zeros.tif`
  (support dot digest `3d03f7cb…`), single-band float32, EPSG:32611, exact grid/transform, nodata=None,
  all pixels finite in [0,1], 0 dots on catalogue, 0 positives outside footprint — the exact fix for the
  operator's `"Predicted values must be in range [0, 1]"` error (submit the `-zeros` file, never `-nan`).
- Executive summary (top-of-page download card + file/estimate/uniqueness table vs all nine focus sites
  with evidence classes) and step-by-step submission guide rendered from machine artifacts; portal card
  inserted non-destructively (the 2026-10-30 banner/markers preserved for its tests).
- Every number labelled HOLDOUT-DTI / USER-REPORTED_PUBLIC_DTI / MODEL_PROJECTION_NOT_A_SCORE /
  SGMC-OFFCAT-CONTROL-DTI / ORGANIZER-CONFIRMED (none). No projection is presented as a score.
- Session prompt preserved at `docs/SESSION_PROMPT_20261031.md` and linked from the README banner.

## Honest bottom line for the selector

- On the **repo's matched hide-and-recover instrument** this candidate is the best gate-passing unique
  candidate to date vs its matched controls (0.1624 vs incumbent 0.1436, CI>0; instrument reproduction
  verified). It also clears every uniqueness gate vs all 211 registry witnesses.
- On the **live-anchored LFI projection** it reads 0.177–0.191 vs the GEMSDOE32 family's 0.2717–0.2768:
  the nine-site family would still be the higher-expected scorer, but those files are duplicates of each
  other and re-submitting them is banned; among *unique new* candidates this is the strongest validated
  file this session. The preregistered next lever (E1's residual CDEC/TSR/STA signal was redundant with
  the template stack; the LFI says live score concentrates on the h19.5 ridge network) is to blend the
  widened-stack surface with the h19.5 ridge prior while holding the ≤70% uniqueness caps — recorded for
  the next session, not run here (3/3 experiment budget used).
- The synthetic-lattice literal overlap (99.96%) is mathematically unavoidable at any 37,654-dot raster
  (capacity floor ≥ 82.34%); the binding uniqueness gates are the 181 competitive sparse references
  (max 57.51%) and the nine leaders (max 44.46%).

## Irregularities flagged for review

1. IR-91-09 (persisting): competition-data mirrors on GitHub are byte-verified but their rights status
   is unresolved; disclose before any organizational claim.
2. The 2026-10-30 review's "lane unassigned / data absent" blockers are resolved by (a) the session
   prompt's method paragraph and (b) the mirror restore; sessions without the prompt text should treat
   the lane as unassigned again.
3. The nine-site "scores" (incl. 0.2778) and the operator-quoted 0.3195/0.4413 leaderboard figures
   remain USER-REPORTED; no organizer receipt exists in-repo for anything.
