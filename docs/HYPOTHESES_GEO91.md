# GEO91 — Candidate geological hypotheses (ranked, 2026-10-25)

Generated before implementation per brief. Every score below is labelled:
**HOLDOUT-DTI** (local hide-and-recover, evaluator version stated) or
**USER-REPORTED** (fleet websites; no organizer receipt exists in this repo).
No number here is ORGANIZER-CONFIRMED.

## Why the fleet best is 0.2778 (USER-REPORTED) — verified mechanism

Forensics re-verified in this session (pinned inputs, sha256-checked;
`docs/s16/gems32-forensics.json` + `evidence/geo91/`):

1. R0 (`h33-h33-2-b2-…-zeros`, 37,654 dots) is **byte-geometry identical** to
   its 40,199-dot parent with the 2,545 dots ≤2 px (200 m) from the mapped
   catalogue removed. Min dot-to-catalogue distance measured here: 2.236 px;
   0 dots on the catalogue; median nearest-neighbour spacing 3.0 px.
2. DTI = T / (0.2·T + 0.2·(S−M) + 0.8·|G|), triangular kernel R=300 m=3 px,
   max-credit per truth pixel. Competition truth is faults **absent** from
   the supplied catalogue, so mass hugging known faults earns ~no T while
   paying full 0.2·(S−M). Pruning it raises DTI mechanically.
3. **Dotting beats drawing lines** under max-credit: contiguous ridge mass
   pays repeatedly for one kernel footprint of credit. Fleet gradient on the
   same lineage: continuous 0.1922 → dotted d1.5 0.2477 → dotted d2.8 0.2600
   → solo 0.2708 → pruned R0 0.2778 (all USER-REPORTED).
4. Caveat: 0.2778 has **no organizer receipt**; GEMSDOE32's own page called
   the file unscored, and its advertised ZIP is a 216-byte archive containing
   an empty ZIP member. The 0.4413 / 0.3195 leaderboard figures in the prompt
   conflict and are likewise unreceipted. The pruning *mechanism* is sound
   DTI algebra; the *causal size* of its live gain is not identifiable here.

**Can >0.2778 be reached?** The fleet plateau (top ~10 of ~90 sites are all
h19-5/d28 dotted derivatives, 0.26–0.278) says the *ranking surface* is
saturated, not the emission. Remaining headroom, in expected-value order:
(1) emission geometry on a strong surface (collar, count, spacing — cheap,
small); (2) genuinely new information catching blind faults (expensive,
uncertain). A catalogue-geometry-only lane cannot beat a geophysics-ranked
surface live; this session tests whether it even beats chance on holdout.

## Ranked candidates not previously implemented in this repo

| # | Hypothesis (layers → signature) | Why off-catalogue? | Difference vs repo | Cost | Status |
|---|---|---|---|---|---|
| 1 | **GEO91-E1 tip+relay geometry** — `existing_faults.tif` only → along-strike tip rays + closing-gap relay + 0.4–1.5 km band×density; dotted, collar >3 px | Mapping stops at cover, faulting doesn't; tips/stepovers are where unmapped continuations live | No repo lane is geometry-only at strict >3 px collar | Low | **TESTED: negative** (below) |
| 2 | **GEO91-E2 habitat-stratified broad coverage** — catalogue density (3 km) → Poisson-disk coverage, density-tilted | Blind faults under basin fill have no surface/geophysical expression used yet; coverage buys kernel lottery tickets where faulting is dense | Fleet "scatter" lanes tilted by geophysics, never pure density+coverage at >3 px | Low | **TESTED: negative** (below) |
| 3 | **Pseudogravity-residual blind contact** — GeoDAWN RTP magnetics + isostatic gravity (competition feature bands) → local transfer-residual edges | Altered/concealed contacts invisible in magnetics alone | S16-PGRD tested a variant: HOLDOUT-DTI 0.0694 (gems57-pooled-hide-v2), lost to gravity-only control — deprioritised, not retried | Med | Not run (prior negative) |
| 4 | **Quaternary-cover thickness edge** — free USGS SGMC geology + depth-to-bedrock proxies → cover-thickness gradient maxima | Faults buried under Lahontan/alluvial cover are systematically unmapped | Requires external raster fetch + alignment audit; SGMC off-catalogue lane scored 0.049–0.051 USER-REPORTED in fleet | High | Not run (data not pinned here) |
| 5 | **Drainage-deflection lineaments** — 10 m DEM (USGS 3DEP, free) → stream-network knickpoint/deflection alignment | Young blind faults deflect drainages before scarps form | Fleet DEM lanes used scarps/curvature, not network topology; 1 m DEM links need login-gated fetch | High | Not run (data not pinned here) |

## Results (this session, 2 of max 3 experiments; 0 slots spent)

Instrument: `gems91-hide-recover-v1.1-nohalo`, whole-segment buffered folds,
features from visible faults only, visible faults masked pixel-exactly,
60,988 withheld positives, 200-draw 5 km block bootstrap.

| Arm | HOLDOUT-DTI | 95% CI |
|---|---|---|
| E1 tip+relay+band geometry | 0.001338 | [0.000671, 0.002171] |
| E1 band-only control | 0.001516 | [0.000727, 0.002245] |
| E1 uniform-random control | 0.076603 | [0.074395, 0.079022] |
| E2 density-stratified coverage | 0.055267 | [0.053367, 0.057308] |
| E2 random-broad control | 0.074387 | [0.071858, 0.076953] |

Leakage canary (protocol rule 4): worst symmetric AUC 0.50691
(`fault_density_3km`) — PASS (<0.90), i.e. no leakage and also no signal.

**Interpretation (the deliverable):** whole-segment buffering deletes the
near-catalogue neighbourhood from training, so any catalogue-proximity
method is structurally starved on this instrument — and density-tilting
actively hurts because withheld complexes leave low-visible-density holes.
This mirrors live fleet evidence (pure relay/tip lanes 0.005–0.016
USER-REPORTED). Catalogue geometry alone does not predict withheld faults.
Beating 0.2778 requires the geophysical feature stack
(`training_features.tif`, 419 MB, restorable via
`python3 scripts/restore_data.py`) with a habitat model at least as strong
as h19-5/d28, plus emission-geometry optimisation — the next session's job.

Non-fault mimic for the lane: mapping-effort bias (catalogue density tracks
exposure/access) and lithologic contacts terminating at cover.

## Official sources (manual review)

- Competition: https://www.drivendata.org/competitions/306/competition-doe-gems/
- Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution
- GeoDAWN surveys (USGS): https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- INGENIOUS: https://gbcge.org/current-projects/ingenious/
- CRS EPSG:32611: https://epsg.io/32611
- Tversky index: https://en.wikipedia.org/wiki/Tversky_index
- GEMS prize PDF (NLR): https://docs.nlr.gov/docs/fy26osti/96647.pdf
