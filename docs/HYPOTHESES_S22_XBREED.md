# Session 22 (`S22-XB`) — Frozen Preregistration

**Official-source re-baselining · natural-experiment decomposition of GEMSDOE32 R0 · PDWC×HGBR cross-breed · live-anchored instrument validation**

- **Branch:** `arena/c722cd53-gemsdoe91` · **Date (UTC):** 2026-10-26
- **Status:** frozen **before** any S22 feature table was used for training, before any holdout / SGMC / LFI / uniqueness number for an S22 candidate existed, and before any S22 GeoTIFF was written. Its SHA-256 is recorded in `docs/run-card-S22-XB.json` (`preregistration.sha256_before_experiments`).
- **Shared evaluator and writer (unchanged, pinned in `registry/template_pin.json`):** `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, 60,988 withheld positives, 80 px buffer, split sha `c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a`) and `vendor/gems57/submission_writer.py`.
- **Budget (protocol Rule 6):** 3 experiments, 2 h wall-clock target, **0 weekly slots spent**. Any overrun is logged, not hidden (`IR-S22-05`).
- **Lane declaration (Rule 1):** the supplied prompt contained **no method paragraph** (the text "Your lane is the single method paragraph below" is followed by nothing). The lane is therefore **self-declared** and logged as `IR-S22-01`: *"execute S21's own ranked next step (cross-breed), and replace hide-v2-only validation by live-anchored validation."*

---

## 0. Official facts verified this session (new; earlier sessions could not fetch these)

Retrieved 2026-10-26 UTC with the Arena web tools. They are **text pages**; no binary data could be downloaded (§3). Receipts: `docs/OFFICIAL_SOURCES_VERIFIED_S22.md`, `docs/s22/official-sources.json`.

| # | Fact | Source |
|---|---|---|
| F1 | Metric is a distance-weighted Tversky index, α = 0.2 (FP), β = 0.8 (FN), triangular kernel `max(1 − d/R, 0)`, R = 300 m; `TP_w = Σ_g max_x p(x)k(d)`; `FP_w = Σ_x p(x)[1 − max_g k]`; `FN_w = Σ_g[1 − max_x p k]`. Worked example 3.00 / (3.00 + 0.2·1.89 + 0.8·2.00) = 0.60. Matches `vendor/gems57/metric.py` line for line. | [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) |
| F2 | **Pixels of known USGS/INGENIOUS faults are masked/excluded from evaluation; they do not count toward penalty terms; re-evaluation also masks them.** | DrivenData staff (`chrisk-dd`), [forum 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516) |
| F3 | "New fault" means **any fault pixel not already captured by USGS/INGENIOUS and can include newly mapped geometry of an existing fault system** (extensions, splays, parallel strands). | `chrisk-dd`, [forum 11536](https://community.drivendata.org/t/where-do-you-draw-the-line/11536) |
| F4 | The public leaderboard score **pools all pixels of the public subset into a single Tversky index**; chunking is not disclosed; the private score is computed the same way; the final re-evaluation is on the **entire GeoDAWN area**. | `chrisk-dd`, [forum 11550](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550) |
| F5 | The organizers **will not disclose** the data sources, fault types or coverage behind the test faults. Phase 2 uses a test set **updated by expert review of Phase 1 submissions**. Reviewers may look at all submissions; **only the selected final submission is scored**. | `chrisk-dd`, [forum 11527](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527), [forum 11579](https://community.drivendata.org/t/phase-2-expert-review-and-phase-1-submissions/11579) |
| F6 | Submission limit is three per week; **the competition-website limit prevails** over the rules' parenthetical. | `chrisk-dd`, [forum 11553](https://community.drivendata.org/t/submission-amount-question/11553) |
| F7 | `deq_n100a15` / `ieq_n100a15` are **INGENIOUS earthquake rate-density layers clipped to GeoDAWN and re-gridded to 100 m** (details in `eq_rate_density_details.docx` of [GDR #1391](https://gdr.openei.org/submissions/1391)). | `chrisk-dd`, [forum 11557](https://community.drivendata.org/t/units-and-very-large-values-in-deq-n100a15-and-meaning-of-ieq-n100a15/11557) |
| F8 | Official Rules (Sept 2026): single GeoTIFF, single layer, 100 m, whole GeoDAWN area; **one final submission across both rounds, chosen without knowledge of private scores "to discourage overfitting to the public test set"**; generative-AI use must be disclosed in the narrative; finalists must deliver code that reproduces results and predicts on new data. | [NLR Official Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) §3.2, §3.4, §3.5, §3.6.2 |
| F9 | Public leaderboard on 2026-10-26: **#1 = 0.4437, #10 = 0.3379, #24 = 0.3169, #50 = 0.2826.** The user-reported 0.2778 (GEMSDOE32 R0) would sit just below rank 50. The briefing's 0.4413 / 0.3195 are earlier snapshots of the same board. | [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) |
| F10 | A rank-5 team publicly described its pipeline as **"20 m lidar-derivative U-Net ensembles, a validation set built from public expert lidar fault picks, calibrated submissions"**. The official reference solution is a U-Net with Tversky loss on the provided 19-band stack. | [forum 11531](https://community.drivendata.org/t/looking-for-a-geologist-teammate-lidar-fault-mapping-basin-and-range-to-join-a-working-ml-pipeline/11531), [reference repo](https://github.com/drivendataorg/gems-prize-reference-solution) |

---

## 1. Novelty audit (eight candidate ideas screened against every prior preregistration and `src/gems91/*`)

| Idea | Repo evidence (grep of `docs/HYPOTHESES_*.md`, `src/`, `scripts/`) | Verdict |
|---|---|---|
| Hydrothermal magnetite-destruction magnetic-low corridors | `H91-3`, `H11-2`, `H15-3`, S12-SPAC: implemented | **Duplicate — rejected** |
| Completeness-weighted PU / catalogue-gap field | `src/gems91/cwp.py` (`CWP91`, 1 km completeness field): implemented, lost on hide-v2 | **Duplicate at another scale — rejected as "new"** |
| Seismicity-residual blind-fault detection | `H11-3` already deferred it; F7 shows the bands are smoothed rate densities | **Killed by data resolution (F7)** |
| Step-over / relay / tip lanes | ≥19 files | Duplicate |
| Accommodation-zone dip-polarity (geophysical fields) | `S17-CRBZ` (`lftg17.py`) | Duplicate for geophysical fields |
| **Orientation-field discontinuity of the *catalogue's own mapped traces*** | structure tensors exist only on geophysical fields (`bhar_s12.py`, S13, S15); **none on catalogue geometry** | **Survives (new layer; concept overlaps CRBZ)** |
| **Joint training of S21 `PDWC` (66 cols) with S18 `HGBR` (16 cols)** | S21 next-step rank 3; never run | **Survives (new combination)** |
| **Fault damage-zone power-law decay prior** (new faults densest near large faults) | no hits for "process zone" / "damage zone decay" | **Survives as a testable claim; existing LFI effects already argue against it (§4, H22-3)** |

---

## 2. Ranked hypotheses (expected live-DTI gain ÷ cost, with access status)

| Rank | ID | Layers | Physical signature | Why it can find faults missing from USGS/INGENIOUS | Differs from the repo by | Non-fault mimic | Expected gain / cost / status |
|---:|---|---|---|---|---|---|---|
| 1 | **H22-5 `LIDAR-SCARP`**: U-Net or matched-filter scarp detector on **USGS 3DEP 1 m** bare-earth DEM derivatives (curvature, openness, break-in-slope, drainage offset) aggregated to 20 m / 100 m | 3DEP 1 m DEM tiles (`1m_DEM_links.csv`); the 19-band stack as context | Sub-metre to metre vertical offsets with along-strike persistence on Quaternary piedmont surfaces; the provenance (F10) that leaders disclose | The experts' labels are drawn on new faults; F10 shows the current leaders train on exactly this layer | The repo has only a pre-aggregated, licence-unchecked 100 m 12-band scarp stack; no trained detector, no 20 m product | Paleoshorelines, fan edges, canals, roads (named by the rank-5 team itself, F10) | **+0.05–0.15 live (evidence: leaderboard spread 0.28 → 0.44). Cost very high; raw footprint ≈ 5.17 × 10¹⁰ px ≈ 207 GB float32. BLOCKED here: 8 official hosts return no connection (§3).** |
| 2 | **H22-1 `XB`**: PDWC66 ⊕ HGBR16 cross-breed, label-blind, joint HGB/LR specialists, **quadrant-budget-equalized** emission (9,413–9,414 dots per quadrant) | 19 sponsor bands only (bitwise `B12/B19`-free sub-model preserved) | Dipping-contact waveform + phase congruency (PDWC) **and** local Hurst/anisotropy regime breaks (HGBR) — two physically different expressions of one fault | Joint model can accept a weak PDWC cue only when a Hurst break agrees, which separates fault edges from lithologic contacts | Never trained jointly (S21 rank 3) | Unfaulted dipping pluton/caldera walls and tilted welded tuff (PDWC), flight-line seams (both) | **+0.005–0.02 hide-v2, live unknown. ~1 h. RUNNABLE → the top feasible hypothesis and the one validated first.** |
| 3 | **H22-2 `STRIKE-DISC`**: structure-tensor **orientation discontinuity of the mapped catalogue** (σ = 3 km), flagging accommodation / transfer-zone corridors | `existing_faults.tif` geometry only | Where two domains of different dominant fault strike meet, extension is transferred by short oblique/strike-slip faults ([Faulds & Varga 1998](https://doi.org/10.1130/SPE323), GSA SP 323, pp. 1–45; [Faulds & Hinz 2015](https://pangea.stanford.edu/ERE/db/WGC/papers/WGC/2015/11100.pdf): 426 systems, accommodation/transfer settings are among the eight favourable ones) | These transfer structures are short, cross-strike and rarely scarp-forming, but **their location is predictable from the known faults' strike field** | First feature derived from catalogue *geometry* rather than from geophysical fields | Survey-block edges that make the catalogue sparse; compilation seams between source maps | +0.0–0.02, uncertain. ~1.5 h. **Not testable on hide-v2** (hiding punches holes that change the orientation field) → LFI factor test only. |
| 4 | **H22-3 `DAMAGE-DECAY`**: new faults densest near large mapped faults, decaying as a power law with distance | `existing_faults.tif` | Damage-zone fracture density decays with distance from a fault | Splays and parallel strands in the same zone count as new (F3) | Not in the repo | Catalogue misalignment copies | ~0 expected: the stored LFI fit (`docs/lfi/fit_r10.json`) gives truth-density factors ×0.61 / ×0.47 / ×0.46 at 1–2 / 2–3 / 3–5 px, ×0.93 at 5–10 px, ×1.16 / ×1.40 at 10–20 / 20–40 px and ×5.94 beyond 40 px — **increasing with distance, i.e. the opposite sign**. Cost ~0.2 h. **Pre-registered kill criterion in §4.** |
| 5 | **H22-4 `SEIS-RESID`**: earthquake-density residual vs mapped-fault proximity | bands 10/16 | Blind faults rupture where no fault is mapped (e.g. 2019 Ridgecrest) | — | — | — | **KILLED before implementation by F7** (smoothed rate density cannot localize to 300 m); same conclusion as `H11-3`. Not run. |

---

## 3. Data-access check for the external hypothesis (H22-5)

Free official sources, all public domain or open data:

- USGS 3DEP 1 m DEM via The National Map downloader — <https://apps.nationalmap.gov/downloader/> (1 m products staged in 10,000 × 10,000 m tiles).
- 3DEP point clouds (EPT) on AWS Open Data — <https://registry.opendata.aws/usgs-lidar/> (`s3://usgs-lidar-public`, no account required).
- GeoDAWN — <https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7>; INGENIOUS/GDR — <https://gdr.openei.org/submissions/1391>; ComCat — <https://earthquake.usgs.gov/fdsnws/event/1/>.

**Obtainability from this sandbox, tested 2026-10-26 with `curl --max-time 10`:** `apps.nationalmap.gov`, `prd-tnm.s3.amazonaws.com`, `usgs-lidar-public.s3.amazonaws.com`, `earthquake.usgs.gov`, `sciencebase.gov`, `gdr.openei.org`, `drivendata.org`, `community.drivendata.org` → **HTTP 000 (no connection) for all eight.** (The Arena *page-fetch* tool reads text pages from some of these hosts but cannot return binary rasters.) H22-5 therefore needs an unrestricted host and a DrivenData login for `1m_DEM_links.csv`.

---

## 4. Experiments (hard cap 3) and decision rules

**E1 — Cross-breed head-to-head (H22-1).** Same folds (`g57_spatial.folds`, buffer 80 px), same seeds, same pipeline. Arm **A** = S21 `pdwc_e1` recipe on PDWC66 only (this doubles as an exact **reproducibility check**: S21 reported `0.181443`). Arm **C** = same recipe on PDWC66 ⊕ HGBR16 (82 columns). Per-fold emission uses an **equal budget of 9,413–9,414 dots per test quadrant** (37,654 / 4). Pooled HOLDOUT-DTI with the shared 1,000-draw 20 km block bootstrap; the **paired** difference C − A is the decision statistic. Every one of the 82 features passes the single-feature leakage canary (symmetric AUC ≤ 0.90, pooled and per quadrant).

**E2 — Live-anchored instrument tests (no holdout; uses the 108 matched USER-REPORTED anchors).**
(a) *Instrument validity*: Spearman of live score against (i) `hide-v2` holdout DTI [S20 reported 0.105 on 112 rasters], (ii) blind SGMC DTI, (iii) the S20 LFI leave-one-site-out prediction. All three recomputed or re-read from pinned JSON, never asserted.
(b) *H22-3 kill test*: refit the unchanged S20 LFI design; **H22-3 is refuted if the fitted truth-density factor for d ∈ (5, 20] px is ≥ the factor for d ∈ (1, 5] px** (already true in `fit_r10.json`; the test is re-run on the fresh fit).
(c) *H22-2 factor test*: add one tercile factor (catalogue orientation-discontinuity) to the S20 design; accepted only if LOSO RMSE does not worsen by more than 0.0005 **and** the fitted high-vs-low effect has a bootstrap 95% interval excluding 1.

**E3 — Emission, uniqueness, gates, TIF.** Final dots from the stitched **4-fold OOF** surface of the better arm of E1, 300 m submodular (CELF) allocation, 37,654 dots, ≥ 3.05 px collar from the full catalogue, zero mass on the catalogue, with hard per-reference overlap caps **built into the allocator**. Written only with `vendor/gems57/submission_writer.py` as an all-finite zeros-encoded float32 GeoTIFF plus a one-TIFF ZIP.

### Gates (computed by code; no human inspection; fail-closed)

| Gate | Pass condition |
|---|---|
| **G1 format** | single band float32, EPSG:32611, 3730×3292, affine `(100,0,243350,0,−100,4508550)`, `nodata=None`, all 12,279,160 cells finite in [0,1], zero positives outside the footprint and on the catalogue, ZIP holds one TIFF byte-identical to the file |
| **G2 uniqueness** | pre-placement surface \|Spearman\| ≤ 0.90 and post-placement 3-px dot overlap ≤ 70% against every **competitive non-blanket** raster (≤ 90,000 dots) in `data/registry`, `data/fleet_registry`, `docs/downloads`, `data/sibling_sweep`; literal all-raster numbers (including the synthetic blankets) are reported next to it, never hidden |
| **G3 leakage canary** | every feature: symmetric AUC ≤ 0.90 pooled and in each quadrant |
| **G4 holdout** | selected arm's HOLDOUT-DTI exceeds both pinned references **S21 `pdwc_e3` 0.195724** and **S18 `hgbr_e1` 0.200742** nominally, and the paired C − A CI excludes 0 |
| **G5 live-anchored** | blinded-refit LFI projection (ridge 10, model-only) ≥ every *independent-model* comparator in the registry (S18 E1, S19 E3, S21 PDWC E3, S20 RHTW E3); LFI-optimized rasters (S20-LFI, S21-FAM3) are excluded as comparators because their projections are optimizer's-curse inflated |
| **G6 informational** | LFI projection vs `R0` (reported, never a gate) |

**Verdict rule.** `OK TO DOWNLOAD = G1`. `OK TO SUBMIT = G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5`. If any gate fails the card says `NO` and names the failed gates. The project cannot choose for the user: the card also prints "SLOTS SPENT: 0".

### What would change my mind

- If arm A does not reproduce `0.181443` (|Δ| > 0.002) the S21 number was not reproducible from the pinned inputs and is reported as such before anything else.
- If C − A is ≤ 0 with its CI including 0, H22-1 is reported as a **measured null**; the TIF is still emitted from the better arm and labelled research-only.
- A live score for any S22 file would be one more equation for the LFI inversion; it overrides every projection here.

---

## Amendment A1 (written 2026-10-26, **before any S22 holdout, projection or TIF number existed**)

Reading `scripts/run_s21_pdwc.py` showed three design details that §4 stated imprecisely. No result had been seen; the amendment is recorded in git before any run.

1. **Equalized-quadrant design = fold-level models only.** S21's `pdwc_e1` evaluated each fold with a *symmetric* surface (12 pair-level models) and a **global** 37,654-dot budget. The "9,413 dots per quadrant" design recommended in S21's next steps needs only the 4 fold-level models per specialist: for fold *q* the surface is the out-of-fold prediction on test quadrant *q*, and **exactly 9,414 / 9,414 / 9,413 / 9,413 dots** (sum 37,654) are emitted **inside that quadrant only**, so no test-quadrant spillover is possible.
2. **Consequence for E1's reproducibility claim.** Arm A under the equalized design is a *different estimator* from S21's `pdwc_e1`, so it is **not expected to equal 0.181443**. Reproducing S21's number needs S21's symmetric design (12 extra fits); it is demoted to an **optional arm `A-sym`**, run only if the budget allows, and its absence will be reported.
3. **Arms and emission.** E1 gets a third, cheap arm **B** = HGBR16 only (14 subsurface-only columns for the sub-model), to show whether the cross-breed gain is additive. Each arm's out-of-fold surface is emitted twice, **NMS** (S21's E1 recipe) and **CELF** (S21's E2/E3 recipe, no reference caps during evaluation); the paired C − A difference is reported for both and **G4 uses the CELF numbers** (the recipe the final file uses). The pinned references 0.195724 and 0.200742 come from the *global-budget* design; they are quoted as external context and G4's nominal comparison to them is reported, but the **decisive G4 statistic is the paired C − A interval under one design**.
