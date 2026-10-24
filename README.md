# GEMSDOE91 — session 2026-10-24 (DrivenData GEMS #306) — PROMPT EMBEDDED

> **HIGHEST URGENCY — MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF. There should be an easy to download submission tif file as described by the prompt. PARALLEL-RUN PROTOCOL: lane is single method paragraph; stay inside; if raster rank-correlation >0.90 or >70% dots within 3px of registry raster, log duplicate and stop. REUSE, DON'T REBUILD: use template's cached feature stack, evaluate_holdout.py and submission_writer.py. LABEL EVERY NUMBER as HOLDOUT-DTI or ORGANIZER-CONFIRMED. LEAKAGE CANARY AUC>0.90 ⇒ leakage. RUN CARD JSON required. BUDGET 3 experiments/2h. No script here submits anything. One entity, three scored slots a week, one final file.**

No script here submits anything. One entity, three scored slots a week, one final file.

## CURRENT STATE

- **Parent:** `R0 = h33-h33-2-b2`, `37,654` unit-mass dots (`RECEIPT`) on the pinned `3730×3292` `EPSG:32611` (`100 m`, `float32`, footprint `5,167,373` px, `0` dots on catalogue, min `2.236 px`) grid. Both pinned TIFFs rebuild byte for byte from either ancestor (`baeae321…c77dd`, `355,443` B; `c55bafc4…6fa9`, `219,065` B; dot digest `905cee9d…`). R0's `0.2778` / `0.3698` remains an unreceipted **CLAIM**.
- **Inputs (`15/15` pinned + `catalogue_px.tif` = `16/16` hash-verified `RECEIPT`):** `scripts/restore_data.py` now restores `training_features` (`gems-geodawn-numerical-features.tif`, `418,912,844` B, sha256 `4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)) from 5 pinned git blobs (`IR-91-25`) and unblocks **all 6 axes** (`MASS`, `CONCENTRATION`, `SNAP`, `PRUNE`, `RELIEF`, `TRACKB`; `scripts/preflight.py` → `BUILD ALLOWED`).
- **Ledger (`54` `BUILT`/`GATED` rows, `0` `SUBMITTED`, `0` live `RECEIPT`s):** `|Δ| < 0.01` = no evidence. **TOP_PUBLIC:** `____` (human must fill, with date) — while it is blank no target number exists, and if it is ≳ `0.35` no built row has a predicted path to it (`SLOT_PLAN.md`). **Slots left this week:** `__ / 3` (`5.7` rolling weeks to unconfirmed `2026-12-03` deadline).
- **Session 8 (`arena/e76f9952-gemsdoe91`) — `MASS` expansion built and gated (IR-91-36, IR-91-37):** the parent's own ranking is **recoverable after all** — the lineage field `anc_h19_5` (`121,131` px) contains all `37,654` R0 dots and leaves `83,477` cells unused (dropped by a 2-px thinning and the collar prune, i.e. by *geometry*), so the next-ranked cells are simply the field cells R0 never took (`vote == 3`, `46,025` of them `>3 px` off the catalogue). Three addition-only arms, unit mass, seed `91024`, **`0` new collar violations** (min added→catalogue `3.16 px`), 15/15 `release_gates` PASS on both encodings:

  | id | pool | dots | added | pred. (`MODEL`) | algebra sweep | SGMC `PROXY` (added vs parent, `≤1 px`) |
  |---|---|---:|---:|---|---|---:|
  | `h33-h33-2-b2-MASSa25adj-20261024-c658eb33` | stacked (8-adjacent) | 47,068 | +9,414 (25.0 %) | **+0.017** | `[−0.009,+0.085]` | `1.16×` |
  | `h33-h33-2-b2-MASSa12adj-20261024-d3de6292` | stacked (8-adjacent) | 42,361 | +4,707 (12.5 %) | **+0.009** | `[−0.004,+0.042]` | **`1.18×`** |
  | `h33-h33-2-b2-MASSa12spc-20261024-d466d2ac` | spaced (no 8-adjacency anywhere) | 42,361 | +4,707 (12.5 %) | **+0.005** | `[−0.003,+0.025]` | `0.96×` |

  Rationale: with `DTI = T/(0.2T + 0.2(S−M) + 0.8|G|)` an added dot needs only `p* ≈ 2–4 %` odds of truth within 3 px to pay, against ~12 % for the lineage's own accepted cells — and count has been raised once in 50 rows, by 10 %. Rejected today with measurements: global translation (enrichment flat over all 25 shifts of ±2 px) and catalogue tip-corridor concentration (`1.37×` vs the parent's `1.60×`).
- **Session 7 (`arena/0ed37053-gemsdoe91`) — `TRACKB` built (Phase 2 only, IR-91-31):** 2,214 strike-consistent traces >=1 km (12,989 support dots) chained from R0 dots ranked by label-blind `S_struct`; three count-fixed arms relocate 10.0%/20.0%/10.0% of lowest-ranked off-trace dots onto traces (`t1k10` `8343ab38` **+0.004** MODEL, `t1k20` `ab72339b` **+0.005**, `t2k10` `6d16fd7a` **+0.002**), each with a per-trace evidence-paragraph GeoJSON. Not in the weekly slot queue unless the human decides.
- **Session 5 (`arena/42de3fed-gemsdoe91`) — `RELIEF` axis built and certified (`IR-91-26`, `IR-91-27`):** Relocates `4,518` dots (`12.00%` moved; `9,036` pixel symmetric diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 → 2,171` `RECEIPT`) across equal-area relief terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)` (single-band leakage canary max AUC `0.5793` `PROXY` `≪ 0.90`):

  | id | value | dots (`RECEIPT`) | T1 / T2 / T3 share (`RECEIPT`) | 4-fold `PROXY` Δ ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) | SGMC `PROXY` Δ ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | predicted (`MODEL`) |
  |---|---|---:|---|---|---|---|
  | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` | `r2p12` (`range->pied`) | 37,654 | 17.7 / 56.3 / 26.0% | −0.0017 | −0.0049 | **+0.006** `[−0.006, +0.018]` |
  | `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` | `r2b12` (`range->basin`) | 37,654 | 29.7 / 44.3 / 26.0% | −0.0032 | −0.0091 | **+0.003** `[−0.010, +0.016]` |
  | `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` | `b2r12` (`basin->range`) | 37,654 | 5.7 / 44.3 / 50.0% | −0.0113 | **+0.0050** | **+0.005** `[−0.010, +0.020]` |

- **Session 6 (`arena/9b8f7d01-gemsdoe91`) — `SNAP` axis built and certified (IR-91-28..30):** first `SNAP` build in the repo. One shared driver (bands 3 `tmi_hg` + 18 `iso_grav_anom_hg`, 600 m high-pass, 1.5 px smoothing), radius 2 px, targets `> 3 px` from the catalogue, R0's `2,171` inherited collar dots quarantined in place (`collar 2,171 -> 2,171` `RECEIPT`), count fixed `37,654` `RECEIPT`, 16/16 `release_gates` + 14/14 `validate_raster` PASS on both encodings:

  | id | rule | dots moved | mean disp. | `MODEL` predicted | SGMC `PROXY` ΔDTI |
  |---|---|---:|---:|---|---:|
  | `h33-h33-2-b2-SNAPs2c-20261023-86b27de1` | 3×3 crest only | 2,047 (5.44 %) | 0.080 px | **+0.000** `[−0.006, +0.006]` | +0.00008 |
  | `h33-h33-2-b2-SNAPs2q75-20261023-8aa75390` | window max, gain ≥ p75 | 4,495 (11.94 %) | 0.237 px | **−0.004** `[−0.012, +0.005]` | −0.00234 |
  | `h33-h33-2-b2-SNAPs2f-20261023-c2391234` | window max, no threshold | 35,174 (93.41 %) | 1.733 px | **−0.014** `[−0.028, +0.004]` | −0.00926 |

  The catalogue PROXY is identically unchanged (`0.006186`, 5 draws, ~12,200 withheld positives, 95 % CI `[0.005958, 0.006413]`) **by construction** — targets are floored at 3 px and the only dots inside 3 px are quarantined, so SNAP cannot touch known-fault credit (IR-91-28). On the independent off-catalogue SGMC map ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) the sign is negative and grows with dose; SNAP is therefore **not** a top-3 slot candidate.

- **Session 8 (`arena/40027ebc-gemsdoe91`) — `CONCENTRATION` on the legal collar, and the queue revised (`IR-91-33`, `IR-91-34`):** 3 arms, count fixed `37,654`, `0` new dot `<= 3 px`, both encodings gated (`PASS`), ledgered with honest predictions: `collar10` (`00cfbe95`, 10.00 % moved, CV `0.6187→0.6037`, **−0.006** `[−0.026,+0.008]`), `collar20` (`106ae19b`, 20.00 %, CV `0.6187→0.5859`, **−0.011** `[−0.051,+0.008]`), and the matched-dose mirror `anti10` (`0e42d6ab`, 10.00 %, **+0.006** `[−0.027,+0.014]`). Measured, not assumed: the collar band carries 1.3x (SGMC) to 2.1x (live-calibrated lineage reference) the per-cell fault credit of the far field, yet moving mass into it **loses** on the only independent fault catalogue (−2.0 % / −3.9 % rel) while uniform-acceptor placement loses less (−0.66 %) and the mirror direction gains (+2.1 %). The catalogue `PROXY` is invariant for this axis by construction (3.05 px floor vs a 3 px kernel), so no local instrument can test the collar hypothesis itself — hence the revised queue below.
- **Merged fleet summary across sessions (`SLOT_PLAN.md`):**
  - **CONCENTRATION** (PR #13, GDR thermal prior): `gdr25rm10` (`c19adb01`, `+0.0123` `MODEL`), `gdr25m10` (`+0.0114`), `gdr10m10` (`+0.0113`).
  - **PRUNE** (PRs #4/#9/#10): delete-only `le3..le15` (`+0.002..+0.010` `MODEL`, `le10` `04002dae` `+0.008`) + fixed-count `p2.5`/`p2.9`/`p4.5px-h19cover`.
  - **MASS** (PR #14, lineage support): `cons1drop` (`−0.000` `MODEL`), `cons2drop` (`−0.015`), `cons3add` (`2803126d`, `+0.009`).
  - **SPACING** (PR #3, radius-2 ring): `spread40` (`6d389309`, `+0.0042` `MODEL`), `clump40` (`−0.0023`), `jitter40` (`0.000`).
- **Session 9 (`arena/4f94d2e7-gemsdoe91`) — `GEOD` geodetic-strain concentration, built & gated 2026-10-24:** `h33-h33-2-b2-GEOD25m10-20261024-bff9fd21` (349 KB nan / 208 KB zeros, sha `bff9fd21…` `RECEIPT`, 37,654 dots, 0 added ≤3 px, 14/14 MUST PASS). Moves 3,765 dots (10.00%, hamming 7,530) from lowest- to highest-prior 2.5 km blocks of the 50/50 geodetic-strain prior (Bands 4+7, AUC 0.579/0.576 PROXY, canary PASS ≪0.90). CV 0.6187→0.610, SGMC off-cat +1.8% rel (+0.0017, independent USGS DS-1052), surrogate strain +31% rel (KAPPA 0.10 → **+0.0090** `[−0.006,+0.020]` MODEL). Rank-corr vs parent 0.8951 (just under 0.90), dot overlap ≤3 px 93% (by construction, 90% dots untouched — flagged per protocol but surface prior is new). **This is the new Slot-1 candidate — first strain-prior file in the fleet, ready to download from `docs/downloads/` and `releases/`.**
- **Next 3 scored slots (`SLOT_PLAN.md`, merged 2026-10-24 across three sessions):** (1) **R0 anchor** (`baeae321`, if no receipt is held) → (2) `MASSa25adj` (`c658eb33`, `+0.017` `MODEL`; supersedes `MASScons3add` `2803126d`, same recall direction at 2.5× the dose) → (3) `MASSa12spc` (`d466d2ac`, `+0.005`, the matched-count geometry control and the safest fallback). Reserves, in order: `PRUNE-le10-norefill` (`04002dae`, `+0.008`, algebra-signed), `PRUNE-le15-norefill` (`1ca1ff6f`), `CONCENTRATIONanti10` (`0e42d6ab`), `GEOD25m10` (`bff9fd21`, new single-prior relocation). **Do not spend a slot on `CONCENTRATIONgdr25rm10`** (`c19adb01`, `+0.0123` `MODEL`): its prediction is a shrinkage of the prior scored against itself. `SNAP` and `collar10/20` stay out.

## What this repo contains

| Path | Purpose |
|---|---|
| `registry/data_manifest.json` | 15 pinned inputs with sha256 + byte length; 3 re-hashed here |
| `registry/r0_verification.json` | Parent hash/grid/dot-count evidence (generated) |
| `registry/preflight.json` | Build-blocked verdict and exactly what is missing |
| `registry/raster_availability.json` | Which of the 20 ledger rows still have a raster |
| `registry/candidate_availability.json` | Hash + format status of the retrievable rasters |
| `src/gems91/metric.py` | DTI re-derivation + exact marginal gain |
| `src/gems91/gates.py` | The MUST gates; an unprovable gate is `UNVERIFIED`, never `PASS` |
| `scripts/` | `verify_parent_r0.py`, `preflight.py`, `validate_release.py`, `pinned.py` CLI |
| `ledger/submissions.csv` | 20 imported rows, provenance in `source`; empty receipt columns |
| `tools/` | `run_concentration.py` (builder), `pins.py`, `raster_io.py`, `stor.py`, `make_fixture.py` |
| `tests/` | 53 tests (metric algebra, gates, ledger invariants, builder, preflight) |

## Run it

```bash
pip install -r requirements.txt
python scripts/verify_parent_r0.py     # fetch pinned parent, verify sha256
python scripts/preflight.py            # BUILD ALLOWED / BUILD BLOCKED
python -m pytest                       # 53 tests, no competition data needed
python -m tools.pins --axis CONCENTRATION   # what an axis still needs, by pinned id
```

### Session 3 delta (`arena/5563ddf8`, same date)

Main had moved twice while this session ran, so this branch was **rebased onto** the merged
work rather than replacing it: the `src/gems91` package, `tools/`, `Makefile`, fixtures and
all 20 imported ledger rows are kept intact.

- **The blocking problem was solved, not worked around.** R0, `sample_submission.tif` and the
  labels raster were recovered from public mirrors and verified against hashes this repo
  already carried. No rebuild from a recipe, no approximation.
- **Parent forensics.** Differencing R0 against solo-d28 proves the lineage's PRUNE is
  delete-only (0 dots in R0 that are not in solo-d28; 2,545 removed at ≤2 px, none added).
- **Three buildable variants**, using `scripts/dti.py` + `scripts/axes.py` + `scripts/build.py`.
- **Two gate implementations now agree** on all three files. Fixing `sha_unseen` to ignore
  BUILT rows (IR-91-12) is what let them certify; before that the gate was unsatisfiable in
  the order the brief prescribes.
- **A real disagreement is recorded, not hidden:** my algebra predicts removal gains, the
  imported `p4px` row predicts −0.009. IR-91-13.
- **Honest about power:** the brief's evidence bar is ±0.01 and only `le15` has a plausible
  path past it. Doses 1 and 2 are refinements.
