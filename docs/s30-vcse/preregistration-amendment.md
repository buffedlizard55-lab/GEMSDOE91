# S30-VCSE preregistration amendment — E3 (recorded before E3 was run)

**Time:** 2026-10-31, after E1/E2 holdout receipts were recorded and before E3
was executed. Experiments used: 2 of 3. Weekly submission slots used: 0.

## What changed

| | preregistered (run-card v1) | amended |
|---|---|---|
| E3 arm name | `vcse_vote_plus_consensus_wide_budget` (44,090 dots @ 2.8 px) | `vcse_supervised_oof_plus_vent` (37,654 dots @ 3.05 px) |
| E3 surface | 0.55·consensus + 0.45·vent-vote | 0.60·supervised-OOF recovery prior + 0.40·vent-vote |

## Why (evidence)

* **E1 (`vcse_vote_scout`) HOLDOUT-DTI = 0.048030 [0.041466, 0.055027]** — below the
  matched random-NMS control **0.070228 [0.067168, 0.072959]** on the
  catalogue-recovery instrument (`gems57-pooled-hide-v2`, 60,988 withheld
  positives). A pure vent-concordance scout does not transfer to held-out
  mapped-fault geometry.
* **E2 (`vcse_vote_plus_consensus`) HOLDOUT-DTI = 0.000000** — the honest 80 px
  hide-and-recover guard zeroes the registry-consensus field around withheld
  components, and the CELF reward sharpening then starves truth
  neighbourhoods; emitted dots (23,287 of 37,654 budget) landed >3 px from all
  withheld truth. The consensus field is anti-informative for this instrument
  once it is stripped of withheld-context leakage.
* The standing protocol promotes only candidates that beat the current holdout
  best (**0.159482**, S27-OSDR E2, same instrument). The remaining experiment
  is spent on the only pattern in the repository that has cleared that bar:
  a supervised out-of-fold catalogue-recovery prior fused with the lane's own
  evidence (S27-OSDR stage-2 pattern, `scripts/run_s27_osdr.py`).

## E3 design (frozen now)

1. **Features (15):** the 13 catalogue-independent VCSE channels + `vent_frac`
   + `struct_frac`. No catalogue-derived feature enters the model.
2. **Supervised stage:** per v3 fold, positives = the fold's **visible**
   catalogue pixels (feature-context legal); negatives = 4× subsample of
   non-catalogue pixels inside the fold's training domain; model =
   `HistGradientBoostingClassifier` with the S25-pinned parameters
   (`max_iter=300, lr=0.06, leaves=63, min_leaf=40, l2=1.0`).
3. **OOF stitching:** each pixel is predicted only by the model that never saw
   its quadrant; Rule-4 canary of the derived OOF surface per fold
   (stop above 0.90 symmetric AUC).
4. **Fusion:** `surface = 0.60·OOF + 0.40·vent-vote`; emission unchanged
   (300 m CELF, budget 37,654, 3.05 px spacing/collar).
5. **Controls:** same matched random-NMS and static-R0 arms as E1/E2.

## What did not change

Metric (`alpha=0.2, beta=0.8`, 300 m triangular kernel), folds
(`label-blind-quadrants-v3-feature-buffered`, buffer 80 px), emitter, budget
family, uniqueness cap (0.64 at packaging), Rule-1/Rule-4 gates, writer,
selection rule (argmax pooled HOLDOUT-DTI), and the zero-slot policy.

---

## Addendum (recorded 2026-10-31, after E3 was executed) — irregularity log

1. **Parameter drift (IR-S30-06).** This amendment froze E3 at 37,654 dots
   @ 3.05 px spacing/collar, but the executed code used the family budget
   **44,090 dots @ 2.8 px** (`BUDGETS["e3"]=44_090`, `SPACINGS["e3"]=2.80`).
   Reported numbers are the executed ones: E3 pooled HOLDOUT-DTI
   **0.052966 [0.046011, 0.060650]** (44,090 dots). Selection rule, metric,
   folds, gates and the zero-slot policy were unchanged. Flagged for review;
   not silently rewritten.
2. **Emitter + gate-set fixes (IR-S30-04/05).** The first packaged raster
   collapsed to 591 dots because the shared CELF emitter applied per-reference
   quotas against dense learning probes (`r11_greedy_mp` etc.) whose 3 px
   halos tile 99.87% of the candidate domain. The duplicate-gate reference set
   is now the nine listed GEMSDOE sites + `data/registry/` (34 sha-unique
   rasters), and the emitter reserves the off-quota share outside the largest
   halo. Final package: 44,090 dots, max 3 px overlap 13.54%, surface |ρ|max
   0.0286. Superseded artifacts: `docs/s30-vcse/superseded/`.
3. **Outcome vs the standing rule.** G5 (blind SGMC >5 px, 500 m) **passed**
   (0.113455 vs parent R0 0.088516), but the pooled HOLDOUT-DTI 0.052966 did
   not beat the registered holdout best **0.159482** → preregistered verdict
   **negative**, weekly submission slots spent: **0**.
