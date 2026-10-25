# GEMSDOE91 · session `bacc7c26` · ISO91 review: analysis, experiment, verdict (2026-10-25)

Evidence labels:

- **HOLDOUT-DTI** — evaluator version, withheld positives and 95% CI given.
- **USER-REPORTED** — typed by the owner. The GEMSDOE32 owner page itself says "NO ORGANISER SCORE EXISTS".
- **PUBLIC-LEADERBOARD** — read from the official page on 2026-10-25.
- **MODEL** — algebra applied to USER-REPORTED scores; a projection, never a score.

No number here is ORGANIZER-CONFIRMED.

## 0. Bottom line

| | |
|---|---|
| New file | `docs/downloads/gemsdoe91-iso91-isolationpu-37654-20261025T190251Z-beaca59b-zeros.tif` (+ single-TIFF `.zip`) |
| SHA-256 | `69bd28b812d333d4eb1912b6dcb82ad500f5d1074d68c8dd7b86f056543d66f2` |
| **OK TO DOWNLOAD** | **YES**: format-valid on three independent re-reads (template validator, card builder, shared download audit) |
| **Uniqueness** | Preregistered protocol registry: **PASS** over 102 rasters, rechecked after merging `main` (S18-HGBR 23.2%, S18-UNIQUE 9.4%; `docs/iso91/registry-recheck.json`). Extended sweep of 977 GeoTIFFs from 102 GEMSDOE repos: **1 marginal literal flag**, 70.1% of dots within 3 px of a 103k-pixel 12GEMSDOE scarp skeleton (chance-corrected 57.7%, dots ρ 0.02), logged as a stop for that scope (G6b) |
| **OK TO SUBMIT** | **NO**: the preregistered holdout gates G1, G2 and G4 failed. ISO91 did not beat the incumbent |
| Slots used | 0. Slot selection is the separate selector's job |
| Recommendation to the selector | No file in this repository beats R0 (GEMSDOE32 h33-2-b2, 0.2778 USER-REPORTED) on any evidence. Keep R0 as the selected submission. |

The automated verdict is reproducible:

```bash
python3 scripts/build_iso91_card.py
python3 generate_submission.py --with-data
```

The first command recomputes every gate from the experiment JSONs. The second re-verifies the advertised bytes.

## 1. Why GEMSDOE32 `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored 0.2778 (USER-REPORTED)

### 1.1 The metric is a budget

The official metric uses α = 0.2, β = 0.8 and a triangular kernel of R = 300 m (3 px).
TPw = Σ_g max_p p·k, FPw = Σ_{p>0} p(1 − max_g k), and FNw = |G| − TPw. Substituting FN gives

  **DTI = T / (0.2·T + 0.2·FP + 0.8·|G|)**

Consequences:

- An isolated new dot with self-credit q and marginal truth credit δT raises DTI only if
  δT·(1 − 0.2·DTI) > 0.2·DTI·(1 − q).
- At DTI = 0.2778 the bar is δT > 0.059 for a miss (q = 0). At 0.4413 it rises to 0.097.
- Because cost is linear in value p, binary dots are optimal for isolated pixels; soft values only matter where dots overlap.
- Along a true line, dots at spacing s keep a mean credit of 1 − s/12 while cutting mass s-fold.
  At s = 2.8 the line keeps 77% of its credit with 2.8× less mass.

### 1.2 Decomposition of the lineage

Scores are USER-REPORTED; geometry is pixel-measured here or in CWP91.

| Step | File | Dots | Score | Gain | Share of gain |
|---|---|---:|---:|---:|---:|
| Source surface | h19-5 ridge network. 1 m/10 m 3DEP openness + local relief, GDR thermal inversion, power-law tip/relay, geopotential worms; catalogue-blind | 121,131 | 0.1922 | — | — |
| Emission | d2.8 dotting of the same ridges | 44,090 | 0.2600 | +0.0678 | **79%** |
| Collar 1 | delete 3,891 dots at exactly 1 px from the catalogue | 40,199 | 0.2708 | +0.0108 | 13% |
| Collar 2 (R0) | delete 2,545 dots at √2–2 px | **37,654** | **0.2778** | +0.0070 | 8% |

### 1.3 What the scores imply (MODEL)

Two independent routes put the public test set at about **12,500 truth pixels**:

- **Lattice route.** The uniform 5 px lattice (206,895 dots) scored 0.0904. Its measured mean
  nearest-dot kernel credit is 0.3748, which implies |G| ≈ 12,530–12,590. The result barely depends on the self-credit ratio.
- **R0 deletion chain.** Assuming the deleted collar dots carried ≈ 0 credit, the chain implies T ≈ 5,070–5,470.
  That is consistent with |G| ≈ 12.5k at T ≈ 5,100.

Hence R0 covers **≈ 40%** of the public truth, with ≈ 36,000 units of FP mass, i.e. about 0.135 TP-weight per dot.
The zero-credit collar dots show that new faults are depleted within 2 px of mapped faults.

### 1.4 Why R0 beats this repository's models

These are the mechanisms, in order of evidence strength:

1. **Allocation.** 69.8% of R0's dots lie more than 1 km from the catalogue (measured). The PU-HGB full-catalogue
   model here puts 27.7% there (measured, `docs/iso91/final.json`). PU posteriors crowd the catalogue halo,
   where new faults are depleted.
2. **Information.** R0's ancestor used sub-100 m topography (1 m/10 m openness and local relief). The 19-band stack
   is 100 m, and B12/B19 cannot resolve the < 2 m piedmont scarps that experts map.
3. **Emission and collar.** These come from §1.2: sparse 2.8 px dots plus deletion of the zero-credit collar.

GEMSDOE91's own PU-HGB submissions scored 0.1823 (S17-LFTG) and 0.1367 (S17-CWPC), both USER-REPORTED.

## 2. Can we beat 0.2778, 0.3195 and 0.4413?

MODEL with |G| = 12,560 and self-credit M ≈ 0.3·T:

| Target | at 37,654 dots | at 15,000 dots |
|---|---|---|
| 0.2778 (R0) | T ≈ 5,081 · coverage 0.405 · 0.135/dot | T ≈ 3,771 · 0.300 · 0.251/dot |
| 0.3195 | T ≈ 5,879 · **coverage 0.468 (+16% TP)** · 0.156/dot | T ≈ 4,364 · 0.347 · 0.291/dot |
| 0.4413 (#1, PUBLIC-LEADERBOARD) | T ≈ 8,268 · **coverage 0.658 (+63% TP)** · 0.220/dot | T ≈ 6,137 · 0.489 · **0.409/dot (3× R0)** |

**Answers:**

- **Beat 0.2778 with a unique file?** Not demonstrated, and not with the 100 m stack alone on current evidence.
  - Every PU-HGB lane here is below R0 live.
  - ISO91 also failed to beat even the PU incumbent on the holdout (§4).
  - A plausible route exists. It combines far-field allocation (R0's strongest trait) with a better localiser,
    so it needs a new information source or a new detector, not another model on the same 19 bands.
- **Beat 0.3195?** This needs +16% truth credit at R0's mass. That is within reach of a better detector, but no such detector exists in this repository.
- **Beat 0.4413?** This needs 63% more truth credit at the same mass, or three times R0's precision at 15k dots.
  - That is only plausible with sub-100 m topography (USGS 3DEP lidar/10 m DEM) plus a learned line detector,
    the reference-solution family (U-Net, Tversky loss 0.2/0.8).
  - The 3DEP hosts are unreachable from this sandbox (§9).
- **About "0.3195".** The user quotes it as a high score. On 2026-10-04 it was #2 (DARD) on the public board.
  On 2026-10-25, #1 is xiaofanhu at 0.4413, #47 is at 0.2833 and #50 at 0.2818 (PUBLIC-LEADERBOARD).
  0.2778 would sit just below rank 50.

## 3. Hypotheses (preregistered before any experiment)

See `docs/HYPOTHESES_ISO91.md` (commit e02f8a7). Ranked:

1. **H1 ISO91, isolation-matched PU (chosen).**
2. H4 cross-modal gradient-vector alignment ridges.
3. H2 footwall-corrected gravity/basement contacts.
4. H3 piedmont-junction dot relocation.
5. H5 USGS 3DEP 1 m/10 m scarp morphometry. This is the highest-potential option, but it is blocked here because the hosts fail TLS.

Two descriptive diagnostics run this session favoured H1 over H2 and H3: the slope-maximum and gravity-gradient offsets are broad.

## 4. Experiments (3 of 3 budget used; 0 slots)

All numbers are **HOLDOUT-DTI**, evaluator `gems57-pooled-hide-v2`, with a paired 20 km block bootstrap (1,000 draws, seed 520810).

**I1 (primary, new live-aligned split).** It withholds every catalogue component with no other component within
500 m, wholly inside an eroded quadrant: 578 components, **11,911 withheld positives**. The hidden set is per fold,
and the models are leave-one-quadrant-out with a 4 km buffer.

| Arm | DTI | 95% CI |
|---|---:|---|
| E0 incumbent (all visible positives) | 0.093105 | [0.075679, 0.111490] |
| **E1 ISO91 (isolated positives only)** | **0.081253** | [0.063850, 0.099617] |
| CTL_HALO (E0, no dots ≤ 5 px of visible faults) | 0.101044 | [0.083480, 0.119965] |
| CTL_SUB (size-matched random positives) | 0.077510 | [0.063381, 0.093973] |
| RND | 0.051483 | [0.046855, 0.055860] |

Paired differences for E1:

| Comparison | Δ | 95% CI | Gate |
|---|---:|---|---|
| E1 − E0 | −0.011852 | [−0.028489, +0.003143] | **G1 FAIL** |
| E1 − CTL_HALO | −0.019791 | [−0.036925, −0.003921] | **G2 FAIL** |
| E1 − CTL_SUB | +0.003743 | [−0.013769, +0.021744] | G3 pass (point estimate) |
| E1 − RND | +0.029770 | [+0.012587, +0.047812] | — |

**I2 (legacy, `buffered_component_draw` seed 20, 11,321 withheld positives).**

| Arm | DTI | 95% CI |
|---|---:|---|
| E0 | **0.085260** | [0.068962, 0.102856] |
| E1 ISO91 | 0.068190 | [0.052142, 0.085391] |
| RND | 0.043165 | [0.037444, 0.048418] |

E0 **reproduces OLC91's recorded 0.085260 exactly**, with identical per-fold scores and positive counts. That verifies the infrastructure.
E1 − E0 = −0.017070 [−0.028221, −0.004979]: **G4 FAIL**, significantly worse.

**Leakage canary (G5).** Each of the 38 features was tested alone against I1 truth. The worst symmetric AUC is 0.6144 (grad det_elev_slope), so it passes.

**Mechanism check.** ISO91 barely moves dots away from visible faults: 8.1–12.6% of its dots lie within 5 px, against 9.5–13.2% for E0.
At 100 m, isolated-fault terrain looks like major-fault terrain. Training on four to five times fewer positives costs more
than the domain match gains. E1 ≈ CTL_SUB says the same thing. **Negative result: isolation-based positive selection is
not a usable lever on the 19-band stack.**

**Secondary observation, a lead and not a claim.** CTL_HALO > E0 on I1 (+0.0079). This is partly built into I1's
500 m separation, so it is not evidence about the live board. The live analogue would be a collar wider than R0's 2 px.
R0 still has 15% of its dots at (2, 5] px, with 2.1× and 1.8× area lift. Testing that is an R0-derivative experiment,
so it belongs to the selector or the R0 owner, not to this lane.

**Report-only blind SGMC off-catalogue control** (never a gate). DTI against SGMC faults more than 500 m from the catalogue:

| File | DTI | Dots > 1 km from catalogue |
|---|---:|---:|
| ISO91 final | 0.071011 | 38.6% |
| E0 final | 0.062879 | 27.7% |
| R0 | 0.088516 | 69.8% (matches the earlier record exactly) |

## 5. Uniqueness (G6)

**Before placement:** the surface's maximum |Spearman| against 100 unique registry rasters is **0.154**. A recheck after merging `main` added S18-HGBR E1 (23.2% within 3 px, ρ 0.035) and S18-UNIQUE (9.4%, ρ 0.007): 102 rasters, maxima unchanged.

After placement:

- The maximum dot |Spearman| is 0.063.
- The maximum non-blanket overlap is **57.7%** of dots within 3 px (`calib_h25ctx_01280`).
- Overlap with R0 is **31.0%**.
- The three blanket references (3 px coverage ≥ 74% of the footprint) are reported both ways:

  | Blanket reference | Literal | Chance-corrected |
  |---|---:|---:|
  | 5 px lattice | 99.88% | 5.9% |
  | r11_greedy_mp | 85.28% | 46.8% |
  | r14_union_tips10_lat6 | 78.41% | 9.7% |

**Extended sibling sweep (G6b, added this session, not preregistered).** Every unique `*/downloads/*.tif` under 20 MB in
the owner's 102 GEMSDOE* repositories was fetched: 979 git blobs, each SHA-1 verified (`docs/iso91/sibling-sweep-sources.json`).
977 were comparable.

1. **Literal reading** (`docs/iso91/sibling-sweep-literal-v1.json`). It flagged **13** rasters. Twelve are dense area
   surfaces or masks with 167k–4.2M positive pixels (32–85% of the footprint) where "dots" is degenerate.
2. **Dense-reference rule** (`docs/iso91/sibling-sweep.json`, identical for every reference).
   - Continuous dense rasters are compared through their matched-budget top-37,654 pixels: maximum overlap
     31.0% (`GEMSDOE48__GEMSDOE48-H57-ds-relief-augmented-20261007-e6b785718c07-diag-belief.tif`).
   - Every raster also gets rank correlation: maximum surface |ρ| 0.45935, maximum dots |ρ| 0.07404.
   - All twelve dense flags clear.
3. **One flag remains.** `12GEMSDOE_r7-nms3-dem10-scarp` is a 103,347-pixel binary skeleton, which counts as sparse
   (≤ 3× our dot count). It has **70.1%** of our dots within 3 px, against a chance level of 29.3%.
   - Chance-corrected: 57.7%. Dots ρ 0.022, surface ρ 0.116.
   - It is just above the literal 70% bar, so it is **logged as a duplicate stop for the extended scope**.
   - Sensitivity only, not the decision: random 37,654-pixel subsets of that skeleton overlap our dots by ~38%.
   - The 3× threshold was set after the literal v1 results were known and was **not** relaxed to clear this flag.

## 6. File, submission form, portal error

- The file is single-band float32, EPSG:32611, 3730 rows × 3292 columns, transform (100, 0, 243350, 0, −100, 4508550).
- **All 12,279,160 cells are finite.** Values are {0, 1}, there is no nodata tag, and cells outside the footprint are 0.
- It has 37,654 dots, none on the catalogue, at a minimum distance of 2.236 px.
- This all-finite zeros encoding removes the portal error "Predicted values must be in range [0, 1]". That error comes from
  NaN or −3.4e38 sentinels or from a nodata tag.
- Name: `gemsdoe91-iso91-isolationpu-37654-20261025T190251Z-beaca59b`.
- Note (102 characters): `GEMSDOE91 ISO91: PU learned only from isolated (>500m) catalogue faults, 37654 binary dots, 2px collar`.

## 7. Three passes

See `PASS_LOG.md` (section "Session bacc7c26"), which records the commands and outcomes.

## 8. Irregularities flagged this session

See `IRREGULARITIES.md`, items IR-91-ISO-01…06.

## 9. Limitations, next steps, access needed

**Limitations:**

- The holdout truth is the catalogue, not expert-mapped new faults. I1 mimics their isolation but not their morphology.
- |G| ≈ 12.5k and R0's ~40% coverage are MODEL inferences from USER-REPORTED scores.
- The sibling sweep covers the owner's public repositories only.
- The fleet-registry inventory is partial (`complete_universal_registry: false`). One pinned row points at a retracted file (IR-91-ISO-03).

**Next steps, ranked by expected value:**

1. H5 on an unrestricted machine. Build 1 m/10 m 3DEP scarp morphometry (multi-scale curvature, local relief, openness)
   aggregated to 100 m, and test it on I1 and I2 against E0 with the same gates. 3DEP is free and public domain.
2. A far-field-allocating emission rule built on the best label-blind posterior, preregistered on I1 with CTL_HALO as the comparator.
3. A selector-level live test of R0's collar width (3–5 px). This is an R0-derivative, outside any lane.

**Access needed:**

- An unrestricted network (or a CI job) to download 3DEP tiles from `prd-tnm.s3.amazonaws.com`, or the competition's `1m_DEM_links.csv` behind the DrivenData login.
- An owner decision on whether the public data mirrors (60GEMSDOE, GEMSDOE) should become private (IR-91-09).

## 10. Official sources (verified this session)

| Source | URL | Verified fact |
|---|---|---|
| Competition home | https://www.drivendata.org/competitions/306/competition-doe-gems/ | Ends Dec 3, 2026 23:59 UTC; $300,000; the same submission is scored in both rounds |
| Problem description | https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ | DTI α 0.2, β 0.8, 300 m triangular kernel; worked example 0.60; EPSG:32611, 100 m, float32, [0, 1] |
| Leaderboard | https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/ | #1 xiaofanhu 0.4413; #50 moongrega 0.2818 (2026-10-25) |
| Rules | https://www.drivendata.org/competitions/306/competition-doe-gems/rules/ → https://www.herox.com/GEMSPrize/resource/2274 | Official rules hosted on HeroX |
| Reference solution | https://github.com/drivendataorg/gems-prize-reference-solution | U-Net by Prof. John Lipor; commit aebe92f (2026-06-16) |
| USGS 3DEP | https://www.usgs.gov/3d-elevation-program/about-3dep-products-services | "All 3DEP products are available, free of charge and without use restrictions" |
| Faulds & Hinz structural settings | https://gdr.openei.org/submissions/355 · https://www.osti.gov/dataexplorer/biblio/dataset/1148722 | Step-overs host ~32% of ~250 Great Basin geothermal fields; terminations 25%; intersections 22% |
| INGENIOUS | https://gbcge.org/current-projects/ingenious/ · https://catalog.data.gov/dataset/ingenious-great-basin-regional-dataset-compilation | DOE award DE-EE0009254; regional fault, geophysics and geochemistry compilations |
