# GEMSDOE91 Limitations & Needs (2026-10-24)

**Current competition state:** Leaderboard high 0.4413 (CLAIM, unreceipted) vs our parent 0.2778 (CLAIM, verified dot set). No ORGANIZER-CONFIRMED receipts in this repo.

## What we cannot do here (and what we need)

1. **No live score.** Every number labelled MODEL/PROXY/HOLDOUT-DTI until a human uploads a file and pastes the receipt. The GEOD prediction +0.0090 is KAPPA=0.10 shrinkage on the strain surrogate, not a score. No slot should be spent without HOLDOUT-DTI +0.006 (brief §5).

2. **Data placement.** The only blocker that ever existed was `data/` placement. It is now solved via `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready (GPU needed for training; metric/losses/validation all verified working here on CPU). In this repo, `scripts/restore_data.py` fetches the same 15 pins from immutable GitHub commits and verifies every SHA256 locally — no `drivendata.org`/`dropbox.com` contact (brief §4.1).

3. **Missing external data for future hypotheses.** The five candidates (H91-A…E) all use *pinned* layers — no new download required:
   - H91-A (GEOD, built): Bands 4+7 (`geod_2ndinv`, `geod_shearrate`) — already in `training_features.tif` (pinned, 418 MB, sha256 4371c82e…).
   - H91-B (depth): Band 15 (`depth_to_base_surf`) — same file.
   - H91-C (radiometric): `ext_geodawn_rad_u8.tif` (pinned, 26 MB, sha256 c22420f7…).
   - H91-D (lidar): `ext_lidar_scarp_u8.tif` (pinned, 36 MB, sha256 d580bb8b…).
   - H91-E (tip): catalogue skeleton derived from `existing_faults.tif` (pinned) — no new data.
   If a candidate needed new official data, the required source would be: USGS National Map 1 m DEM for lidar re-derivation (free, https://apps.nationalmap.gov/) or UNAVCO GPS strain (free, https://www.unavco.org/) — both obtainable, but not needed for the top candidate.

4. **Inherited collar (IR-91-03).** R0 has 2,171 dots at 2–3 px from the catalogue (min 2.236 px). Every non-PRUNE child inherits them. The brief says “≥3 px unless AXIS=PRUNE” — if enforced strictly, any GEOD/CONCENTRATION/MASS file is non-compliant at birth. The gates report this as `collar_ge_3px = FAIL (inherited)` and pass everything else. Human must rule on whether the gate binds controlled edits of R0 or only new-dot placement.

5. **Disk & compute.** Each build needs ~1.5 GB RAM and 30–90 s CPU for the full 3730×3292 grid. The GEOD build peaked at 1.5 GB and was killed once by the sandbox before light recovery succeeded. On a laptop/desktop, `python scripts/build_geod.py --build` reproduces the exact sha `bff9fd21…` byte-identically (deterministic, no RNG).

6. **Weekly cap.** One entity, 3 scored slots per rolling week, 1 blind final file. Promotion to a real slot is a *separate selector step* within the cap shown on the submission page — do not pick submissions here. Negative results are deliverables (run card verdict `negative`).

7. **Manual verification required.** Every sha in `registry/data_manifest.json` must be re-hashed on the entrant’s machine (`scripts/restore_data.py` does this). No competition raster is committed (`data/` and `releases/*.tif` are gitignored; only `docs/downloads/*.tif` is the submission artifact and is committed for Pages).

## What still needs human decisions

- TOP_PUBLIC score + date, slots left this week, and R0 receipt (action 0, costing no slot).
- Which file goes in which slot, and the blind final pick (see SLOT_PLAN.md).
- Whether to rebasing on PRUNE-le3 (35,483 dots) for strict 3 px compliance.
- Deadline confirmation (unverified 2026-12-03).
- Upstream mirror visibility (IR-91-09).

No credentials are read/requested/stored; no leaderboard scraping; no label probing; no region-isolated patterned files (brief §4.5).
