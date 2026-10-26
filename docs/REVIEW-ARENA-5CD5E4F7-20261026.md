# Current checkout review — 2026-10-26

**Branch:** `arena/5cd5e4f7-gemsdoe91` (fixed for this session)

**Decision:** **NO NEW TIFF GENERATED. OK TO DOWNLOAD: NO NEW CANDIDATE. OK TO SUBMIT: NO.**

**Experiments:** 0 / 3. **Weekly slots used:** 0. **ORGANIZER-CONFIRMED score:** none.

This review follows the repository's standing brief and parallel-run protocol. It does not spend a submission slot or select a real submission. The user-facing nine-site executive summary and pinned source audit already exist at [`high-score-submissions-review.html`](high-score-submissions-review.html), [`nine-site-audit-20261026.html`](nine-site-audit-20261026.html), and [`research/nine-site-audit-20261026.json`](research/nine-site-audit-20261026.json). The current branch status is recorded in [`run-card-ARENA-5CD5E4F7-20261026.json`](run-card-ARENA-5CD5E4F7-20261026.json).

## Pass 1 — inspect current checkout and prior work

- Read the README standing brief and the existing nine-site audit, executive summary, current portal, shared holdout/evaluator/writer tooling, experiment plan, and data manifest.
- The user-supplied order for the requested nine rows is retained as **USER/OWNER-REPORTED, UNVERIFIED**: GEMSDOE32 0.2778; GEMSDOE36 0.2750; GEMSDOE28 0.2710; GEMSDOE31 0.2708; GEMSDOE33 0.2632; GEMSDOE25 and GEMSDOE30 0.2600; GEMSDOE24 0.2477; GEMSDOE27 0.2449. It is arithmetic over the prompt, not a verified leaderboard.
- The prior audit records source repositories at pinned commits and describes cross-site repeats/lineage. Those are owner-repository facts, not organizer receipts. The precise GEMSDOE32 0.2778 entry has no receipt binding the score to TIFF bytes in the audited manifest; therefore it is a forensic benchmark only. A newly merged parallel review on `main` records an official public-leaderboard observation of 0.4437 (rank 1, retrieved 2026-10-26). This branch did not independently refresh that page; the public-board value is not an organizer receipt for any focus-site TIFF. See [`REVIEW-ACTIVE-8F9CFF19-20261026.md`](REVIEW-ACTIVE-8F9CFF19-20261026.md) for the copied observation and provenance.

## Pass 2 — reproduce blockers and avoid unsafe output

- `registry/experiment_plan.json` has `lane: null`; the prompt says “single method paragraph below” but contains no assigned method paragraph. The top prior proposal is not authorization to substitute a lane.
- `data/` is absent. After installing the exact pinned `requirements.txt` packages in ignored `.venv/`, `scripts/experiment_preflight.py` failed closed because assignment is absent and `data/official/sample_submission.tif` does not exist. `scripts/preflight.py --json` reports 0/2 required inputs verified and blocks all six axes.
- No feature surface, complete candidate-vs-registry check, buffered hide-and-recover evaluation, per-feature leakage canary, final-dot check, or TIFF validator could be run. Every score estimate, uniqueness pass, and raster-format claim is therefore null/not-run in this run card.
- No prior TIFF was copied, renamed, or reissued as a “unique” candidate. That would not satisfy novelty or validation.

## Pass 3 — user-facing clarity and regression testing

- Updated the README top block and root landing page so the active branch says no new TIFF is cleared, identifies the 0.2778 value as unverified, and links the nine-site executive summary and run card.
- Added a current-status panel at the top of `docs/index.html`. It explicitly distinguishes older download links (historical research) from current approval. The pre-existing portal still contains an identity mismatch: its older S21-PDWC card appears first, while `docs/current-run.json` points at S20-RHTW. Both historical artifacts state `OK TO SUBMIT: NO`; this review does not choose between them, and the new banner overrides them as current approval status.
- Preserved the earlier source-pinned audit and its hypothesis ranking rather than silently changing old evidence. Its ranked proposals are qualitative and not predicted scores. Hypothesis 1 (dipping-contact waveform matched-filter bank) is documented but remains untested and cannot be adopted as the lane without assignment. The free official source leads for external-data options are listed in that audit; coverage/access were not verified for this review, so they are not marked viable.
- Added this branch-specific run card and review note. No submission name, note, score estimate, TIFF hash, or validator PASS is fabricated.

## Evidence and research boundary

The site-by-site score table is the requested report and labels each historical decimal USER-SUPPLIED / UNVERIFIED. Its rationale for the GEMSDOE32 progression (sparse emission and catalogue-near pruning reduce redundant/low-utility prediction mass under a distance-tolerant metric) is explicitly a plausible metric mechanism, not causal proof or a private-test score. No claim that any prior artifact was organizer-scored is made without an organizer receipt.

Official/manual-review links in the prior report include DrivenData's problem, rules, data page and leaderboard; the official reference solution; USGS 3DEP, USGS SGMC, USGS ComCat, Landsat Collection 2 surface temperature, and the DOE/NLR report. This current pass did not fetch those live external pages. The pinned owner-site source records are linked in the JSON register. A provided link is not represented as freshly verified content.

## Next steps / limitations

1. Provide the actual assigned method paragraph and its assignment source; do not infer it from one of the old experiments.
2. Resolve authorized placement of exact, hash-verified sample/template/parent/catalogue/features and the complete registry. The DrivenData data portal is login-gated in recorded history; this checkout has no access or local inputs.
3. Confirm the shared `vendor/gems57` evaluator/writer hashes against the prescribed template snapshot, then run the exact blocked spatial holdout and every single-feature leakage canary, under the three-experiment/two-hour budget.
4. Run pre-placement surface rank correlation and 3-pixel overlap before placement; stop and log duplicate if `|rho| > 0.90` or overlap `>70%`. Repeat on exact final dots, then validate finite values in `[0,1]` and exact CRS/shape/transform.
5. Only a positive, reproducible holdout result plus passed checks can enter a separate selector step. No automated process here can authenticate the private competition receipt or choose a weekly slot.

## Verification record

- Dependency install: **PASS** from `requirements.txt` into ignored `.venv/`.
- Experiment preflight: **BLOCKED as expected**; missing assigned lane and `data/official/sample_submission.tif`.
- Build preflight: **BLOCKED as expected**; 0/2 required inputs verified; six axes blocked.
- Test suite after merging latest `main`: **PASS — 682 passed, 9 skipped; 89 Rasterio Affine pending-deprecation warnings** (`pytest -o addopts='' -q`).
- Result is workflow-negative, not a scientific negative finding. See the single JSON run card for all required nulls and labels.
