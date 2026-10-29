# DEF4A160 Review — 2026-10-29 — arena/def4a160-gemsdoe91

## Executive decision

**NEGATIVE / RESEARCH ONLY. New unique 20k-dot TIF generated, OK TO DOWNLOAD: YES — research only, OK TO SUBMIT: NO.**  
One heuristic experiment (SCBR-lite without ML) plus one attempted HGB OOF (killed by OOM, not counted). No weekly slot used. Do not treat any historical fabric or nine-site leader as this session's approved submission.

- **New TIF:** `gems91-def4a160-heuristic-20000dots-20261029T143925Z-a52e392d-zeros.tif` (20,000 dots, SHA256 `b9ec1edf27ab7734073bae6ad9617900c540341ea062ff979ed0828ebf45e054`, single-TIFF ZIP beside it) — passes local format validator (all-finite [0,1], EPSG:32611, 3730×3292, 100 m), no dots on catalogue, zeros outside footprint.
- **Why OK TO SUBMIT is NO (all automated):** (1) HOLDOUT-DTI 0.05989 [0.05434,0.06606] does **not** beat matched base control 0.06460 (paired delta -0.00471 [-0.00723,-0.00230]); (2) literal all-registry dot overlap is 100% vs the 206,895-dot lattice (the lattice's 3-px dilation covers 99.87% of footprint — any spread 20k-dot raster is geometrically forced to near-100% vs that calibration blanket; competitive ≤90k and nine-site scopes **do pass**); (3) selector step pending (protocol rule 6). What DID pass: leakage canary (max 0.596 ≤0.90), surface |rho| 0.078 ≤0.90, nine-site dot overlap 34.95% ≤70%, competitive ≤90k 39.72% ≤70%.
- **Highest claimed among nine:** GEMSDOE32 0.2778 USER-REPORTED (no organizer receipt), but all nine leaders are one duplicate family (88–100% peer overlap). Not a new unique submission.

## Nine-site table (re-audited 2026-10-28, still current)

See `docs/nine-site-20261028/nine-site-leaders-20261028.json` and `docs/s25/nine-site-audit.json` for hashes. Scores below are USER-REPORTED claims, not ORGANIZER-CONFIRMED.

| Site | File (pinned SHA) | Reported | Unique vs other eight? | Guidance |
|---|---|---|---|---|
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` `68d0e2e4…` 60,069 dots | 0.2477 | NO — 88.48–100% 3-px overlap | Do not re-submit (duplicate) |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` `91eae1ca…` 44,090 dots | 0.2600 | NO — 88.17–100% | Do not re-submit |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` `33003374…` 61,328 dots | 0.2449 | NO — 86.72–98.02% | Do not re-submit |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` `5556aa14…` 37,660 dots | 0.2710 | NO — 95.47–100% | Do not re-submit |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` `8cf893ea…` 44,090 dots | 0.2600 | NO — 88.17–100% | Do not re-submit |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` `07b6db44…` 40,199 dots | 0.2708 | NO — 95.39–100% | Do not re-submit |
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` `c55bafc4…` 37,654 dots | **0.2778 USER-REPORTED best among nine** | NO — 99.88–100% | Benchmark only, do not re-upload |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` `87f857d5…` 41,865 dots | 0.2632 | NO — 92.64–99.71% | Do not re-submit |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` `e1589102…` 38,854 dots | 0.2750 | NO — 97.31–97.58% | Do not re-submit |

**Why 0.2778 led and can it be beaten?**  
R0 is the best-pruned member of the H19-5 ridge family (S22 lineage): `h19-5` 121k-px worm (0.1922) → 2.8-px NMS 44,090 dots (0.2600) → delete ≤1 px collar 40,199 dots (0.2708, pixel-identical on GEMSDOE28/31) → delete (1,2] px 37,654 dots (**0.2778**). Under DTI = T/(0.2T+0.2FP+0.8|G|) with 300 m triangular kernel and max-per-truth-pixel credit, dots near mapped faults are masked and contribute pure 0.2·FP, while a second nearby dot adds no T credit if kernel already covered that truth. Pruning redundant/collar dots improves precision without new detector. Closed-form predicts the next two scores within 0.001; implied recall ≈38–42% at ≈0.135 per-dot credit. Public #1 0.4544 (2026-10-28 fetch) needs ≈1.6× R0's per-dot credit or ≈35% more recall — requires **new information**, not retuning the same ridge. In-repo ranked path to that is 1 m lidar scarp morphometry (USGS 3DEP, CC0) on an unrestricted host (sandbox cannot fetch `tnmaccess.nationalmap.gov`; see LIMITATIONS). This session's heuristic demonstrates a geometrically feasible (20k) unique geometry but its holdout is below the matched single-feature control, so no new high-score projection is claimed.

## New heuristic TIF from this session (research only)

| File to download (research) | Estimated leaderboard score (labelled) | Unique vs GEMSDOE24/25/27/28/30/31/32/33/36 and registry? | OK? |
|---|---|---|---|
| **DEF4A160 heuristic** <br> [`gems91-def4a160-heuristic-20000dots-20261029T143925Z-a52e392d-zeros.tif`](../downloads/gems91-def4a160-heuristic-20000dots-20261029T143925Z-a52e392d-zeros.tif) <br> ZIP beside it <br> SHA256 `b9ec1edf27ab7734…` 20,000 dots | **ORGANIZER-CONFIRMED: none.** MODEL projection: none calibrated (LFI not refit). **HOLDOUT-DTI 0.059891 [0.054345,0.066057]** `gems57-pooled-hide-v2`, v3 folds, 60,988 withheld — *not a leaderboard score*; base control 0.064597, paired delta -0.00471 [-0.00723,-0.00230] | **YES vs nine** 34.95% max within 3 px ≤70%; **YES vs competitive ≤90k** 39.72% ≤70%; **NO vs literal all** 100% vs `calib_r13lattice_00904` (206,895 dots, 99.87% footprint coverage — geometrically forced) — capacity lower bound at 20k is 66.76% vs that one blanket | **Download: YES — research** <br> **Submit: NO** — holdout not beating control + lattice literal + selector pending |
| S25-FABRIC E2 (2026-10-28 prior) | HOLDOUT-DTI 0.147741 [0.12976,0.16756] (v3, 60,988) — best v3 repo holdout, beats base control +0.022997 [+0.01427,+0.03187]; LFI MODEL projection 0.0792 (not a score) | YES vs nine 40.19%; NO vs competitive 74.89% vs BHAR; literal 98.75% vs lattice | NO (competitive duplicate + low projection) |
| Best nine claim = GEMSDOE32 | 0.2778 USER-REPORTED (prompt) | NO — 99.88–100% peer duplicate | NO as new unique |

**Validation gates (automated, no human inspection):**

| Gate | Result | Detail |
|---|---|---|
| Leakage canary max symmetric AUC ≤0.90 | PASS | 0.5960 (heuristic) over 4 feature folds, 161 clusters |
| Surface |rho| ≤0.90 before placement | PASS | 0.0778 vs `calib_h161_01855` (max among 62+64+downloads) |
| Final dots ≤70% vs nine leaders | PASS | 34.95% max |
| Final dots ≤70% vs competitive ≤90k | PASS | 39.72% max |
| Final dots ≤70% vs all incl. dense lattice | FAIL | 100% vs `calib_r13lattice_00904` — geometrically forced; see capacity bound |
| Paired HOLDOUT beats best matched control | FAIL | delta -0.00471 CI entirely below 0 |
| Format: single-band float32 all-finite [0,1] EPSG:32611 3730×3292 `nodata=None` zeros outside, 0 on catalogue | PASS | `validate` all 15 checks PASS, `submission_writer` + independent re-read PASS, ZIP roundtrip PASS |
| Live projection ≥ R0 (if used) | FAIL | not computed; SGMC diagnostic not run this lite session |

## Irregularities flagged

- **IR-DEF4A160-01** Self-assigned lane (prompt has no single method paragraph; `lane:null` at start). Recorded, not claimed as coordinator assignment.
- **IR-DEF4A160-02** Lattice capacity bound: at 37,654 dots literal 70% impossible (82.34% lower bound); reduced to 20,000 (66.76% bound, feasible by capacity) to make a checkable candidate, but measured overlap remains ~100% because the lattice covers 99.87% of footprint within 3 px — any spread raster is near-100% vs that one calibration blanket. Competitive and nine-site scopes are the decision-relevant scopes; literal blanket scope is reported, not silently exempted.
- **IR-DEF4A160-03** HGB OOF attempt killed by OOM (exit -9) on 3.8 GiB host; counted as not-run, not hidden. Heuristic is the sole measured experiment (1/3 budget used).

## Reproduce

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python scripts/restore_data.py
python scripts/restore_registry.py --available-only
python scripts/experiment_preflight.py  # NOT_RULED_OUT at 20k
PYTHONPATH=src:. .venv/bin/python -u scripts/generate_heuristic_def4a160.py
python scripts/audit_downloads.py --output docs/download-audit.json --html docs/download-audit.html
```

Maximize P(Win) · Own the Outcome. Negative result is a deliverable. No slot used.

