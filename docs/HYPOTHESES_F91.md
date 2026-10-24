# F91 hypotheses — preregistered 2026-10-24 (before any F91 holdout number)

Session lane (self-assigned; the brief contains no single assigned method
paragraph — IR-91-S11-01 pattern, flagged not hidden): **FUSE91**, the
single method paragraph frozen here before any F91 surface is scored:

> Train a HistGradientBoosting classifier on the union of (a) the 28
> HGB-CTX features (19 sponsor-band footprint percentiles + TRI3
> concordance percentile + eight 11×11 context means), (b) the 18 ASC91
> antisymmetric cross-fault step features, and (c) six new
> depth-conditioned subsurface-contact features defined in
> `src/gems91/fuse91.py`; emit unit dots by the repo's greedy spaced
> placement (2.8 px, 37,654 budget) from the predicted surface, with the
> emission variants E1/E2/E3 below. No previous submission raster is read
> as an input, mask, ranking or prior. The catalogue is used only for
> training labels inside the training area and for the candidate
> exclusion distance, both re-derived from the *visible* catalogue in
> every holdout fold.

## Why 0.2778 led the fleet — the forensic answer this lane is built on

Verified from pinned bytes (`evidence/forensics_f91_20261024.json`,
RECEIPT) and the GEMSDOE32/GEMSDOE25 sites fetched 2026-10-24:

1. **It is an emission, not a detector.** R0 (37,654 dots) is *exactly*
   `d2.8 minus dots with d(catalogue) <= 2 px` and *exactly*
   `solo-d2.8 minus d <= 2 px` (both subset identities byte-verified).
   The full claimed-score (CLAIM, no organizer receipt in any repo;
   GEMSDOE32's own page calls the B2 file UNSCORED with a 0.2747
   projection) chain is: H19-5 solid surface 121,131 px (0.1922) →
   dot-thin 1.5 px 60,069 (0.2477) → dot-thin 2.8 px 44,090 (0.2600) →
   solo 40,199 (0.2708) → B2 collar prune 37,654 (0.2778 CLAIM).
2. **Thinning wins because the metric saturates.** TPw takes a *max*
   over predictions within 300 m of each truth pixel, so the second dot
   covering the same truth pixel adds ≈0 TPw but still pays
   α·(1−k) of FPw. Removing redundant mass raises credit per dot at
   almost no TPw cost until the marginal dot's credit reaches the
   break-even bar α·DTI (≈0.0556 at DTI 0.2778; derived in
   `vendor/gems57/metric.py`, cross-checked vs `scripts/dti.py`).
3. **The ≤2 px prune removes provably-dead mass.** Dots within 200 m of
   a catalogue fault spend most of their 300 m kernel on already-mapped
   (non-test) fault pixels; the nested-pair algebra inversion (MODEL,
   assumptions in the forensics JSON) implies those dots carried ≈0
   hidden credit: two independent nested pairs imply denominator
   18,802 / 19,691, TPw ≈ 5,223 / 5,470, hidden |G| ≈ 14.1k / 15.2k px
   (H28's independent fit: 12,691), credit/dot ≈ 0.139–0.145. The prune
   *keeps* 2,171 flank dots at 2–3 px — exactly where a parallel splay
   or stepover strand sits relative to a mapped trace.
4. **The ancestor detector was mostly topographic.** R0 dots vs
   footprint background: strongest single-band enrichment is
   `det_elev_slope` (AUC 0.661) and low `tc` (symmetric 0.630), then
   `tmi_hg` (0.578) — a multiline topographic/openness detector with
   potential-field corroboration, consistent with its H19 lineage name.

**What beating it requires (arithmetic, MODEL):** at the same mass and
|G| ≈ 14k, DTI 0.32 needs credit/dot ≈ 0.160 (+15 % over R0) and the
verified current leaderboard #1, 0.4413 (official leaderboard page read
2026-10-24), needs ≈ 0.220 (+58 %). No emission tweak on the same
surface supplies that; the surface's *ranking* (credit density at the
top) must improve, and placement must respect the ≈1.85 px
localization scatter of hidden traces around detector ridges
(GEMSDOE25 H28 fit; GEMSDOE32 Monte Carlo: covering the
scatter-smoothed field beat covering the sharp field by +0.014 to
+0.025 under that truth model, MODEL not organizer score).

## Ranked candidate hypotheses (all sponsor-band, licence-clean)

| # | Hypothesis | Layers / signature | Why it catches catalogue-missing faults | Difference from implemented lanes | Non-fault mimic | Expected gain / cost |
|---|---|---|---|---|---|---|
| F91-1 (LANE, E1) | **Step×context fusion**: a supervised model that sees raw band context *and* odd-symmetric cross-fault steps *and* depth-conditioned conductivity residuals ranks concealed faults with higher credit density than any single view | B1–B19 percentiles + TRI3 + mean11 contexts; ASC step bank on B12/B13/B2/B15/B17 at 8 strikes; new: conductivity (B17) percentile residual within depth-to-basement (B15) deciles, its gradient/Laplacian, B15 & B13 Laplacians, curvature-polarity concordance | Catalogue faults are exposure-biased (mapped where scarps show); a buried normal fault still steps gravity/magnetics/basement/conductivity across strike even with no scarp, and depth-conditioning removes the basin-fill conductivity trend that masks piedmont contacts | ASC91 tested steps *alone* (0.1168); HGB-CTX tested context *alone* (0.142885); their fusion was ASC91 §6's top recommendation and was never run. The 6 depth-conditioned features are new in this repo (REVIEW-20261024 rank-1 untested candidate, now implemented as features) | Buried volcanic/intrusive margin (steps every field at once); saline/clay conductivity contact | Highest expected HOLDOUT-DTI gain (two near-orthogonal, individually-validated views: ASC surface |ρ| ≤ 0.1374 vs registry); medium cost (feature caches exist as code) |
| F91-2 (E2) | **Scatter-cover emission**: hidden traces sit σ≈1.85 px off detector ridges, so covering the Gaussian-smoothed (σ=1.85 px) fused surface earns more expected kernel credit than covering sharp ridge tops | F91-1 surface → Gaussian σ=1.85 px → same greedy spaced 2.8 px emission | Expert-labelled new faults are drawn on the *true* trace; geophysical crests are systematically offset from traces (dip, depth, RTP shift). Catalogue holdout truth is pixel-aligned with the training labels, so this arm may *lose* on holdout while winning live — the instrument disagreement GEMSDOE32 measured; selection rule below stays holdout-conservative | Every prior lane here emitted from the sharp surface; GEMSDOE32's smoothfield arm was a Monte Carlo on someone else's surface, never a shipped de novo detector here | None (emission geometry, not geology); risk = wasted mass off-ridge in range fronts where the surface is already trace-aligned | +0.014…+0.025 under the H28 truth MODEL (GEMSDOE32 MC); low cost (one convolution) |
| F91-3 (E3) | **Collar-ring emission**: reclaim R0's flank geometry with de novo dots — allow 2 < d(catalogue) ≤ 3 px but cap ring dots at 6 % of budget (R0's measured 5.77 %), all other dots > 3 px | F91-1/F91-2 winner surface + tiered greedy emission (`fuse91.tiered_greedy_spaced`) | New faults include splays/stepovers 200–300 m from mapped traces; every lane in this repo since DENOVO discarded that ring entirely (> 3 px), while the fleet-best file kept 2,171 dots there | R0's ring dots are inherited ancestor dots; ours are placed de novo by surface rank with an explicit cap so the ring cannot flood the budget with catalogue-halo detections | The catalogue fault's own geophysical halo (detector fires beside the mapped trace, dot duplicates it at 250 m offset) — controlled by the 6 % cap and by holdout (ring is re-derived from *visible* faults only) | Unknown sign on holdout (that is the test); low cost |
| F91-4 | Depth-conditioned conductivity residual as a standalone unsupervised detector | B17 residual-by-B15-decile gradient × B13 edge concordance | Piedmont faults under conductive basin fill | Implemented here only as F91-1 features; standalone arm not run (budget) | Saline groundwater / clay lens | Lower than F91-1 alone (CED-style unsupervised arms reached ≤0.09); low cost, deferred |
| F91-5 | 1 m DEM lidar scarp fusion | USGS 3DEP 1 m DEM (competition's `1m_DEM_links.csv` / The National Map, free & official) → sub-100 m scarp height/coherence aggregated to 100 m | Experts label new faults largely from lidar-visible scarps invisible at 100 m | Repo's pinned `ext_lidar_scarp_u8` is licence-unchecked (manifest: "do not redistribute") and provenance-unverified (IR-91-40), so it is **not used**; 3DEP hosts are outside this sandbox's egress allowlist (github/pypi/npm only) | Shoreline terraces, roads, field boundaries | Potentially the largest live gain (leaderboard gap analysis) but **not viable in this session**: source is obtainable free from USGS 3DEP on an unrestricted machine, not from here. Named, checked, deferred — not proposed as viable now |

## Frozen experiment plan (budget: exactly 3, protocol §6)

Instrument (identical to the DENOVO/HGB-CTX/ASC receipts so numbers
compare): `build_denovo.fold_setup` whole-component checkerboard folds
(400 px blocks), 60,988 withheld positives, exclusion and training
negatives re-derived from visible components only, pooled official DTI
via `scripts/dti.py` (α=0.2, β=0.8, R=3 px), 37,654-dot budget split by
fold footprint share, spacing 2.8 px. HGB hyperparameters reused
verbatim (`build_denovo._train_hgb`). No distance-to-catalogue feature.

- **E1** = F91-1 features (28 CTX + 18 ASC + 6 NEW = 52), sharp surface,
  > 3 px collar. Comparable prior best on this instrument: HGB-CTX
  **0.142885** HOLDOUT-DTI (receipt `evidence/holdout3_hgbctx_20261024.json`).
- **E2** = E1 fold surfaces Gaussian-smoothed σ=1.85 px before emission
  (F91-2), everything else identical (same trained models; emission only).
- **E3** = winner of (E1, E2) by pooled HOLDOUT-DTI, plus the F91-3
  collar ring (2 < d ≤ 3 px, cap 6 % of each fold's budget).
- **Selection rule (frozen):** the final build uses the arm with the
  highest pooled HOLDOUT-DTI among E1–E3. Promotion gate: that arm must
  beat 0.142885 on the identical instrument, pass the leakage canary
  (every feature alone, symmetric AUC ≤ 0.90), pass pre-placement
  surface novelty (|Spearman| ≤ 0.90 vs enumerated registry) and
  final-dot novelty (directed ≤ 70 % within 3 px vs every *real*
  registry raster; the synthetic lattice calibrator — which rejects R0
  itself at 99.9 % — is reported separately with symmetric F1, never
  silently dropped), and pass all format validators on the exact
  written bytes. If the gate fails, verdict is negative / NOT OK TO
  SUBMIT and no slot is recommended. All scores are HOLDOUT-DTI; no
  organizer score is claimed or projected as a score.

Controls computed with the same folds for context (not experiments):
seeded random spaced dots at matched count (reproduces the DENOVO
receipt 0.070827 if the instrument is identical — an instrument
identity check), and the SGMC off-catalogue control (REPORT ONLY).
