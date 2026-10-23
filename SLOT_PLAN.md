# SLOT PLAN — after PRUNE ladder extension (2026-10-23)

**Parent R0** `h33-h33-2-b2` (37,654 dots, 2.236 px collar floor). R0's 0.2778 is CLAIM.
Three new PRUNE delete-only variants built this session (all 14/14 gates PASS):

| # | variant | dose | n_dots | % changed | predicted (MODEL) |
|---|---|---:|---:|---:|---|
| A | `PRUNE-le4-norefill` | ≤4 px (3825) | 33,829 | 10.16% | +0.003 [−0.003,+0.009] |
| B | `PRUNE-le5-norefill` | ≤5 px (5637) | 32,017 | 14.97% | +0.005 [−0.004,+0.013] |
| C | `PRUNE-le10-norefill` | ≤10 px (11360) | 26,294 | 30.17% | +0.008 [−0.006,+0.019] |

Ledger now 29 BUILT, 0 SUBMITTED. TOP_PUBLIC and weekly slots still need human fill.

## Next three scored slots (in order)

| order | candidate | mechanism / predicted result | what the receipt changes |
|---|---|---|---|
| 1 | **PRUNE `le10-norefill`** (`04002dae`) | Largest delete-only dose this session; denominator saving vs new-fault credit. Predicted +0.008 MODEL, only dose with plausible >0.01 path. Tests whether mass far from known faults is background. | If **+0.01 or more** vs R0: field is over-massed away from catalogue; keep pruning (bisection beyond 10 px or refill-held at 10 px once ranking is available). If **|Δ|<0.01**: PRUNE neutral at this dose; try `le4`/`le5` to check monotonicity. If **≤−0.01**: halo carries real truth; stop pruning, add mass at 3–5 px (MASS add) or switch to RELIEF/CONCENTRATION. |
| 2 | **PRUNE `le4-norefill`** (`360fe57e`) | Refines 3→4 px collar (1,654 new dots, all zero catalogue credit). Predicted +0.003 MODEL. Cleanest test of the 300–400 m band outside the organiser's "within 300 m" clause. | If slot-1 was **positive** but small: `le4` should also be positive and smaller; its gain confirms linearity. If slot-1 was **flat/loss**: `le4` isolates whether the 3–4 px band is the first losing band — its sign locates the optimum inside 4–10 px. |
| 3 | **SPACING `spread40`** (`6d389309`) | 40% of densest dots to emptiest ring-2 cell (same set/budget as `clump40`/`jitter40` controls). Predicted +0.004 MODEL, bounded ≤0.003 by uniform-truth ceiling. Retires geometry if flat. | If SPACING **flat** (|Δ|<0.01) after PRUNE: arrangement is not a lever; spend remaining slots on block-scale prior (RELIEF or CONCENTRATION with external prior) and on getting a receipt for the baseline. If SPACING **gains** ≥0.01: clusters waste credit; next is spread at 50% / ring-4 or anisotropic packing. |

*These are proposed values, not submitted; check `ledger/submissions.csv` for (parent,axis,value) dupes before construction — these three are new and unique.*

## Weeks to deadline (deadline unconfirmed: 2026-12-03 on competition page)

- **Now / wk 1:** submit slots 1–2 (PRUNE doses). Paste receipt_score/date into ledger the same day. Treat |Δ|<0.01 as **no evidence** (public chunks only; private chunks may differ). Submit no more than 3 scored files per rolling week (one entity rule).
- **Wk 2:** submit slot 3 (SPACING) only if PRUNE results are interpretable (|Δ| pattern, not all flat). Otherwise spend slot 3 on a confirmation of the best PRUNE dose (re-validate format from disk, re-upload same file is forbidden — build `le7`/`le8` bisection instead).
- **Wk 3–4:** combine the two best axes (e.g. PRUNE at winning threshold + RELIEF tercile shift or CONCENTRATION with a licensed prior) if human supplies `training_features.tif` and a licensed prior; otherwise confirm the best single-axis file and build its fallback twin (`-zeros.tif`) and re-validate both from disk.
- **Wk 5–6 / by 2026-12-03:** choose one final file **blind** (no peeking at private-chunk feedback), plus a fallback, re-validate format of both (`validate_raster.py` must print PASS), and submit the final file. No agent submits.

## Better axes to consider later (not built this session)

1. **MASS-SHAPE at fixed count (refill-held PRUNE).** Mechanism: delete the low-gain `max_px` halo *and* refill to 37,654 from the parent's own marginal-gain ranking, so mass is held constant and only placement changes. Confounder: ranking itself is confounded with catalogue distance. Falsifier: refill-held PRUNE scores *below* delete-only at same dose → mass loss, not placement, drove the prior gain. Requires `training_features.tif` ranking artifact.
2. **RELIEF tercile shift.** Mechanism: faults concentrate at range-front/piedmont vs basin; move 10–15% of dots from basin to range-front terciles of detrended elevation (from `ext_lidar_scarp_u8.tif` bands). Confounder: lidar scarp signal tracks survey geometry / lithologic contacts, not faults. Falsifier: both directions (basin→range and range→basin) score within 0.01 of each other → relief does not transfer. Blocked this session only by time, not inputs (RELIEF is READY).

Human must supply before spending a slot: `TOP_PUBLIC` with date, weekly slots remaining, and confirmation of the competition deadline. Do not contact drivendata.org/leaderboard pages programmatically.
