# GEMSDOE91 — CURRENT STATUS (OLC91, 2026-10-25) — read this first

> **OLC91 session (`arena/3444a6d3-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH ONLY` · `OK TO SUBMIT: NO`.**
> **[⬇ Download the GeoTIFF](docs/downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif)** ([ZIP](docs/downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.zip)) · SHA-256 `35259f3a…82abf8dc` · [JSON run card](docs/run-card-OLC91.json) · [Site](https://buffedlizard55-lab.github.io/GEMSDOE91/) · [Executive summary / how to submit](docs/executive-summary.html) · [Preregistration + results](docs/HYPOTHESES_OLC91.md)
>
> * **Lane (declared, none was supplied):** Oriented Line-integral Coherence. A PU-HGB posterior on the 19 official bands is multiplied by its own 1.1 km strike-coherent line support, then emitted as 37,654 dots with no dots on or within 2 px of the catalogue.
> * **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, buffered whole-component draw seed 20, 11,321 withheld px / 606 components, LOQO): E1 **0.0832** [0.0669, 0.1005] · E0 incumbent recipe **0.0853** [0.0687, 0.1023] · random **0.0432** [0.0377, 0.0485]. Paired E1−E0 **−0.0021** [−0.0045, +0.0002], with E1 lower in 4/4 folds. **Result: NEGATIVE.** Not comparable with v1.0 numbers such as S14-PTAC 0.267782.
> * **Uniqueness:** surface max |ρ| 0.216 (PASS). Final dots: 76.8% within 3 px of `gems91-bhar-e3` (71.8% chance-corrected), against a 70% limit, so **DUPLICATE-STOP**. This compared 90 unique rasters, including 62 fleet rasters.
> * **Format:** PASS (float32, EPSG:32611, 3730×3292, exact transform, 0 NaN, values in [0,1], 0 dots on the catalogue). **Canary:** PASS (max AUC 0.601). **Slots used:** 0. **Experiments used:** 1 of 3.
> * **Why 0.2778 (USER-REPORTED):** h19-5 catalogue-blind ridge network → 44,090 dots (0.2600) → delete 3,891 dots at 1 px (0.2708) → delete 2,545 dots at √2–2 px (**0.2778**). 70% of its dots are more than 1 km from mapped faults. Beating the public top 0.4413 needs a better localiser, at about 0.62 coverage against R0's ≈0.38. Full analysis: [docs/HYPOTHESES_OLC91.md](docs/HYPOTHESES_OLC91.md).

Core values: **Maximize P(Win) · Own the Outcome.** Every number is labelled HOLDOUT-DTI or USER-REPORTED. Nothing is ORGANIZER-CONFIRMED without a submission-page receipt. Read the preserved [full standing prompt](#full-project-brief) every session.

---

## Parallel sessions merged on main the same day (S17-CDSC, XG91, S17-CGRD; all OK TO SUBMIT: NO)

> **SESSION 17 (`S17-CDSC`, branch `arena/1722e30a-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> 105-feature Prevalence-Calibrated Faulds–Hinz En-Echelon Relay Auto-Context + 16 Local (`<= 1 km`) `S15` Subsurface-Junction / Multi-Wavelength Salem / Aquifer-Baffle Stage-2 Fusion + `72`-col Bitwise `B12`/`B19`-Invariant Pure-Subsurface Specialist: remediates `IR-91-S15-06` (`Test_k / Train_k` prevalence alignment `1.45x/1.56x -> 1.03x/1.09x`, lifting Fold 1 `NE` by **`+0.058247`** from `0.273196` to **`0.331443`**), `IR-91-S15-07` (excluding `>= 3 km` GDR/S12 regional bowls from Stage-1), and `IR-91-S15-05` (`72`-col bitwise `B12`/`B19`-free Stage-2 specialist). Winner **`E1 = 0.259972 HOLDOUT-DTI`** (`95% CI [0.244333, 0.275361]`, `E2 = 0.259854`, `E3 = 0.252062` on `gems91-hide-recover-v1.0` = `v1.1-nohalo`, `60,988` withheld), jumping **`+0.019339`** over `S15-SCGF E2` (`0.240633`) and beating `S13-PTHA E3` (`0.244601`) by **`+0.015371`** (`paired 95% CI [+0.010244, +0.021122]`, `P(>0) = 100%`). External non-calibration fleet 3-px overlap is **`53.16% <= 70% PASS`** (`43.76% <= 70% PASS` vs `GEMSDOE32 R0`), but submission remains fail-closed (`0.259972 < 0.267782 S14-PTAC E2`; literal all-raster lattice overlap `99.834%`); zero weekly slots spent (`slots_used = 0`).
> [Download GeoTIFF](docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif) (`sha256: 39aaac68…21836`) · [Single-TIFF ZIP](docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.zip) · [Audit](docs/s17-cdsc.html) · [Executive summary](docs/s17-cdsc-executive-summary.html) · [Run card](docs/run-card-S17-CDSC.json) · [Preregistration](docs/HYPOTHESES_S17_CDSC.md) · [3-Pass review](docs/REVIEW-S17-CDSC-20261025.md) · Form note (`95/140`): `S17-CDSC E1 research only: HOLDOUT-DTI=0.2600; ext3px=53.2%, r13_blanket=99.83%; do not submit.`

**XG91 session (2026-10-25): OK TO DOWNLOAD: YES — research only. OK TO SUBMIT: NO. NOT OK TO SUBMIT.** A new GeoTIFF was generated and re-read from disk. It is not approved for a weekly slot.

- Download: [docs/downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif](docs/downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif) · [ZIP](docs/downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.zip) · [site](docs/index.html) · [how to submit](docs/executive-summary.html) · [run card](docs/run-card-XG91.json)
- Name: `gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros`
- Note (86/140): `XG91 E1 crest; HOLDOUT-DTI 0.071171 gems57-pooled-hide-v2; below random; do not submit`
- SHA-256: `4aecf0851bbe0ae3a9f87255f4d438597becc90e50ec49789852cfe1a33d4327`
- **0.071171 HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 60,988 withheld positives, 95% CI [0.063769, 0.079270]). Matched random control **0.073788 HOLDOUT-DTI** (same evaluator and population). Paired delta **−0.002618**, 95% CI [−0.009427, 0.005131], includes zero. No improvement over chance is established.
- Leakage canary PASS (max symmetric AUC 0.55182). Method-raster 3 px overlap 31.035%. Synthetic lattice overlap **99.742%** — literal duplicate stop; E2 and E3 were not run. 0 slots spent. `ORGANIZER-CONFIRMED: null`.
- The prompt's assigned method paragraph was absent. XG91 was preregistered in [docs/HYPOTHESES_XG91.md](docs/HYPOTHESES_XG91.md) before scoring and is not an orchestrated lane. Do not treat the download button as upload approval.

The public leaderboard, fetched 2026-10-25 from the DrivenData page, shows rank 1 at 0.4413. That is not a receipt for this file. The GEMSDOE32 page fetched the same day says no organiser score exists for `h33-h33-2-b2`; the user-reported 0.2778 remains unverified. Read the [standing brief](#full-project-brief) at the start of every session.

> **SESSION 17 (`S17-CGRD`, branch `arena/cbdb6e26-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — FORMAT-CERTIFIED RESEARCH` · `OK TO SUBMIT: NO — NEGATIVE VERDICT`.**
> Cooper–Cowan Multi-Altitude Theta-Map / Hyperbolic-Tilt Edge Invariants (`B02 rtp` + `B13 iso_grav_anom` at $z=200\text{ m}, 600\text{ m}, 1500\text{ m}$) + DOE GDR-1391 Chemical Geothermometer Disequilibrium ($\Delta T_{\text{eq}}$) Upflow Plumes + Prior-Shift-Calibrated Subsurface Auto-Context (`34` columns, provably `B12`/`B19`-blind and never reading `dist_known_fault_px`):
> - **Remediates `IR-91-S15-06` & `IR-91-S15-07`:** applying `gems91.ptha.prior_shift_calibrate_surface` to all 6 pairwise 2-quadrant Stage-1 splits before stitching local auto-context and subtracting $\ge 3.2\text{ km}$ regional bowls causes **`E2` (`0.092125 HOLDOUT-DTI`, `95% CI [0.081283, 0.102562]`) to improve strictly (`+0.008144` / `+9.7%` relative) over `E1` (`0.083981 HOLDOUT-DTI`, `95% CI [0.074440, 0.093453]`)** on `gems91-hide-recover-v1.0` (`60,988` withheld positives), and scores **`0.225235 HOLDOUT-DTI`** (`95% CI [0.197388, 0.252846]`) on `gems57-pooled-hide-v2` (8 km label-blind quadrants). `E3` (`0.132279 HOLDOUT-DTI`, `95% CI [0.121610, 0.142760]`) is logged as a Rule-1 duplicate stop (`77.51% > 70%` 3-px dot overlap with DEM-inclusive sibling `SPID-E3`) and never written as a submission.
> - **Passes all 42 real registry & download rasters:** `E2` pre-placement surface max $|\rho| = 0.08657 \le 0.90$, final dots max $|\rho| = 0.03162 \le 0.90$, and final dots max 3-px overlap $= 56.06\% \le 70.0\%$ (`PASS`), while remaining blocked under the literal 89-file synthetic lattice capacity bound (`calib_r13lattice_00904.tif` $\ge 82.34\%$) and trailing `S14-PTAC E2` (`0.267782 HOLDOUT-DTI`). Zero weekly slots spent (`slots_used = 0`).
> - [Download S17-CGRD E2 GeoTIFF](docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif) (`203,212 B`, `sha256: 287af6b2df1c34080c55cd1aef9264f30e5e507b152ff31dcb94d13cf6f521a6`) · [Single-TIFF ZIP](docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.zip) (`164,903 B`, `sha256: b3f52073…c324f8f`) · [Audit](docs/s17-cgrd.html) · [Submission guide](docs/s17-cgrd-executive-summary.html) · [Run card JSON](docs/run-card-S17-CGRD.json) · [Preregistration](docs/HYPOTHESES_S17_CGRD.md) · [3-Pass review](docs/REVIEW-S17-CGRD-20261025.md) · Form note (`96/140`): `S17-CGRD E2: Cooper-Cowan Theta+GDR diseq+cal-AC; HOLDOUT-DTI=0.0921; SGMC=0.0578; research only`


> **`arena/4975419d-gemsdoe91` review:** [Three-pass review](docs/REVIEW-4975419D-20261025.md) · [Run card](docs/run-card-4975419d.json) · [Executive guide](docs/executive-summary.html) · [Automated download audit](docs/download-audit.html). Parallel review merged from main: [review and access findings](docs/REVIEW-SESSION-20261025.md).

## Historical status records (not current-branch results)

# GEMSDOE91 — PREVIOUS STATUS (GEO91, 2026-10-25, superseded)

> **Active Arena checkout review (`arena/85ad3c12-gemsdoe91`, 2026-10-25): NO new experiment or TIFF; OK TO SUBMIT: NO.** See [current-checkout three-pass review and hypothesis shortlist](docs/REVIEW-ACTIVE-85AD3C12-20261025.md) and [machine-readable review card](docs/run-card-85ad3c12.json).

**Site / download:** `docs/index.html` leads with the current GeoTIFF and its verdict.
**Current file:** `gems91-geo91e2-stratcover-collar3-20261025T132527Z-zeros.tif`
(37,654 dotted px, collar >3 px, SHA-256 `57d2c44c…e5befe2f`) — **OK TO DOWNLOAD: YES ·
OK TO SUBMIT: NO** (HOLDOUT-DTI 0.055267 [0.053367, 0.057308],
gems91-hide-recover-v1.1-nohalo, 60,988 withheld, loses to matched random
control 0.074387; format/canary/uniqueness PASS; 0 slots spent).
Machine verdict: `docs/run-card-GEO91.json`. Why 0.2778 (USER-REPORTED, no
organizer receipt) leads the fleet and what beating it requires:
`docs/HYPOTHESES_GEO91.md`. Core values: **Maximize P(Win) · Own the Outcome.**
Every number is labelled HOLDOUT-DTI or USER-REPORTED; nothing is
ORGANIZER-CONFIRMED without a submission-page receipt.

---

# GEMSDOE91 — a new TIFF, an honest automated verdict

> **Session 17 (`S17-CWPC`, 2026-10-25, branch `arena/4f695c18-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — FORMAT-CERTIFIED` · `OK TO SUBMIT: NO — RESEARCH NEGATIVE` (`slots_used = 0`).**
> Restored all 15 SHA-256-pinned competition inputs (including the 418.9 MB 19-band `gems-geodawn-numerical-features.tif`, 4-band radiometrics, 12-band LiDAR scarp stack, and off-catalogue USGS SGMC control) plus 62 fleet reference rasters (`scripts/restore_data.py`, `scripts/restore_registry.py`), preregistered 5 ranked geological hypotheses in [`docs/HYPOTHESES_S17_CWPC.md`](docs/HYPOTHESES_S17_CWPC.md), and executed the 3-experiment **Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence + Cover-Conditioned Upward-Continuation Attenuation + Coulomb Strain-Strike Slip-Tendency + Prior-Shift-Calibrated Local Auto-Context** (`S17-CWPC`) lane (`src/gems91/cwpc17.py`, `scripts/run_s17_cwpc.py`).
> - **Holdout Results (`HOLDOUT-DTI`, 60,988 withheld positives):**
>   - `gems57-pooled-hide-v2` (8 km whole-segment buffer): **`E1_cwpc_physics_hgb` (16 label-blind CWPC physics features alone, zero topographic bands) = `0.082658 HOLDOUT-DTI`** (`95% CI [0.073949, 0.091793]`, `+0.011325` vs `random_null`); **`E2_cwpc_integrated_hgb` (43 features) = `0.131810 HOLDOUT-DTI`** (`95% CI [0.114159, 0.147689]`, `+0.060477` vs `random_null`, `+0.049153` vs `E1`); **`E3_cwpc_calibrated_dual_autocontext` (43 features + 8 prior-shift-calibrated local $\le 900\text{ m}$ auto-context features including `B12`/`B19`-blind `ac_subsurf_cal`) = `0.122467 HOLDOUT-DTI`** (`95% CI [0.105656, 0.137559]`, `+0.051133` vs `random_null`, `+0.039809` vs `E1`).
>   - `gems91-hide-recover-v1.1-nohalo` (60,988 withheld positives): `E1 = 0.044412`, **`E2 = 0.089250`**, **`E3 = 0.086573 HOLDOUT-DTI`** (`+56.6%` over `GEO91-E2 = 0.055267`, but below repo best `S14-PTAC = 0.267782`).
>   - **Blind Off-Catalogue USGS SGMC Control (`SGMC-OFFCAT-CONTROL-DTI`):** **`0.090912`** (`62,122` off-catalogue bedrock/concealed fault pixels $> 300\text{ m}$ from `existing_faults.tif`, exceeding `E3`'s own `v1.1-nohalo` catalogue score `0.086573` by `+0.004339`).
> - **Automated Gates:** Format PASS (`EPSG:32611`, `3730×3292`, `float32`, `nodata=None`, all `12,279,160` cells finite in `[0, 1]`, `37,654` binary `1.0` dots, `0` on-catalogue, `min_catalogue_distance_px = 3.1623 > 3.0 px`); Leakage Canary PASS (43 base + 8 fold auto-context features tested, worst symmetric AUC `0.62714 <= 0.90`); Registry Uniqueness PASS vs pinned `GEMSDOE32 R0` (`34.97% <= 70%` 3-px dot overlap, `|rho_surface| = 0.05927 <= 0.90`) and vs all 43 repository rasters (`max 3-px overlap = 51.92% <= 70%`), while disclosing `99.06%` overlap against the `206,895`-dot synthetic blanket lattice `calib_r13lattice_00904.tif` (Pigeonhole lower bound `82.34%`).
> - **Submission Name:** `gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros` · **Note (`115/140` chars):** `S17-CWPC cross-wavelet phase-lag+cal AC; 37654d [0,1] collar>3px; HOLDOUT-DTI=0.1225 (gems57-v2); research negative`
> - [Download S17-CWPC GeoTIFF](docs/downloads/gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.tif) (`sha256: 792af6255a7e1048e5c2053c178feee5f807f5de83b5d07e51617a7164115ec5`) · [Single-TIFF ZIP](docs/downloads/gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.zip) (`sha256: e36c855d7ee93fed60ad5d8c18d32d0d4e748ff204539fa638f6e8faca9d24b4`) · [Run Card](docs/run-card-S17-CWPC.json) · [Preregistration & Forensics](docs/HYPOTHESES_S17_CWPC.md)
>
> **Session 17 (`S17-EULR`, branch `arena/597b6f3f-gemsdoe91`, 2026-10-25): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> Euler-deconvolution source-geometry fusion (windowed 11×11 px least-squares Euler solutions, structural indices 0/1, on B14+B09 magnetics and B13 gravity with FFT vertical derivative; 14 label-free density/depth/uncertainty features) tested by frozen single-change ablation on the shared hide-and-recover holdout: `E1` (S13 recipe control) `0.198824`, `E2` (+Euler) `0.199155`, **`E3` (Dinkelbach winner) `0.249626`** (`95% CI [0.234678, 0.264996]`) **`HOLDOUT-DTI`** (`gems91-hide-recover-v1.0`, `60,988` withheld; identical v1.1-nohalo receipt) and **`0.100737` Blind Off-Catalogue USGS SGMC DTI** (`+0.005351` vs `GEMSDOE32 R0 = 0.095386`, report-only). Paired Euler effect `E2−E1 = +0.000331` (`95% CI [−0.002264, +0.003222]`, includes 0) ⇒ **Euler block is a measured null in this fusion**; `0.249626 < 0.267782` (S14-PTAC comparable best, point comparison only — no paired test vs S14 attempted); literal registry gate fails (synthetic lattice `99.827%`; S13 sibling `93.836%` — the S13-descendant family converges to near-identical dot sets); zero weekly slots spent.
> [Download GeoTIFF](docs/downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif) (`sha256: 3d07dcb8…69d2`) · [Single-TIFF ZIP](docs/downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.zip) · [Run card](docs/run-card-S17-EULR.json) · [Preregistration](docs/HYPOTHESES_S17.md) · [Review & 0.2778 post-mortem](docs/REVIEW-S17-EULR.md) · Form note (`79/140`): `S17-EULR E3: Euler deconv fusion; HOLDOUT-DTI=0.2496; 44000 dots; HOLD selector`

> **Session 17 (`S17-CDSC`, branch `arena/1722e30a-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> 105-feature Prevalence-Calibrated Faulds–Hinz En-Echelon Relay Auto-Context + 16 Local (`<= 1 km`) `S15` Subsurface-Junction / Multi-Wavelength Salem / Aquifer-Baffle Stage-2 Fusion + `72`-col Bitwise `B12`/`B19`-Invariant Pure-Subsurface Specialist: remediates `IR-91-S15-06` (`Test_k / Train_k` prevalence alignment `1.45x/1.56x -> 1.03x/1.09x`, lifting Fold 1 `NE` by **`+0.058247`** from `0.273196` to **`0.331443`**), `IR-91-S15-07` (excluding `>= 3 km` GDR/S12 regional bowls from Stage-1), and `IR-91-S15-05` (`72`-col bitwise `B12`/`B19`-free Stage-2 specialist). Winner **`E1 = 0.259972 HOLDOUT-DTI`** (`95% CI [0.244333, 0.275361]`, `E2 = 0.259854`, `E3 = 0.252062` on `gems91-hide-recover-v1.0` = `v1.1-nohalo`, `60,988` withheld), jumping **`+0.019339`** over `S15-SCGF E2` (`0.240633`) and beating `S13-PTHA E3` (`0.244601`) by **`+0.015371`** (`paired 95% CI [+0.010244, +0.021122]`, `P(>0) = 100%`). External non-calibration fleet 3-px overlap is **`53.16% <= 70% PASS`** (`43.76% <= 70% PASS` vs `GEMSDOE32 R0`), but submission remains fail-closed (`0.259972 < 0.267782 S14-PTAC E2`; literal all-raster lattice overlap `99.834%`); zero weekly slots spent (`slots_used = 0`).
> [Download GeoTIFF](docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif) (`sha256: 39aaac68…21836`) · [Single-TIFF ZIP](docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.zip) · [Audit](docs/s17-cdsc.html) · [Executive summary](docs/s17-cdsc-executive-summary.html) · [Run card](docs/run-card-S17-CDSC.json) · [Preregistration](docs/HYPOTHESES_S17_CDSC.md) · [3-Pass review](docs/REVIEW-S17-CDSC-20261025.md) · Form note (`95/140`): `S17-CDSC E1 research only: HOLDOUT-DTI=0.2600; ext3px=53.2%, r13_blanket=99.83%; do not submit.`
>
> **DRN91 session (2026-10-25, this branch): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> First drainage-routing lane (D8 flow-accumulation/deflection/knickpoint on B12 + 19 sponsor bands, cross-fitted HGB, 37,654 dotted zeros TIFF).
> `E1 drainage-only = 0.163754`, **`E2 = 0.166217` HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 60,988 withheld; CI in run card) — below S14-PTAC 0.267782 comparable best, so promotion gate FAILED and 0 slots were spent. Leakage canary max AUC 0.594 (pass). Uniqueness within this repo's indexed downloads: max |Spearman| 0.143, max 3-px dot overlap 64.6% (pass, local scope only).
> [Download GeoTIFF](docs/downloads/gems91-drn91-e2-37654dots-20261025T134012Z-4a2e588a-zeros.tif) (sha256 `b1623999…a19fe3`) · [Executive summary](docs/drn91-executive-summary.html) · [Run card](docs/run-card-DRN91.json) · [Preregistration](docs/HYPOTHESES_DRN91.md)
>
> **UNIQUE SUBMISSION (`unique-offcatalogue-damagezone`, branch `arena/e6fdea6b-gemsdoe91`): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — FORMAT-CERTIFIED` · `OK TO SUBMIT: NO — RESEARCH NEGATIVE`.**
> Damage-zone annulus lattice (1 km lattice, 3 px < d_catalogue <= 10 px): 8,718 unit dots, value 1.0 at dots, 0 elsewhere, NaN outside footprint; EPSG:32611, 3730x3292, 100 m, single-band float32, all values in [0,1]. **HOLDOUT-DTI = 0.0 (CI [0,0], 60,988 withheld) — deliberate off-catalogue negative.** Registry uniqueness: surface |rho| 0.00983 (<= 0.90), dots within 3 px 20.67% (<= 70%) — NOT a duplicate. Zero weekly slots spent.
> [Download GeoTIFF](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif) (`sha256: a5636b10…ca11`) · [Single-TIFF ZIP](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.zip) · [Audit](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-audit.json) · [Run card](docs/run-card-unique-offcatalogue-damagezone.json) · Form note (140/140): `Unique off-catalogue damage-zone lattice; format-certified unique GeoTIFF; HOLDOUT-DTI=0.0 deliberate negative; research download only`

> **2026-10-25 repository safety review (`08e91dad`): OK TO DOWNLOAD — RESEARCH ONLY; OK TO SUBMIT — NO.** No new TIFF generated: method-lane assignment is missing and prior duplicate stops remain binding. [All-download audit](docs/download-audit.html): **55** registered TIFF/ZIP files inspected against restored SHA-pinned sample/catalogue references; **48 technical PASS, 7 FAIL**. Technical PASS never authorizes a slot. [Three-pass review and ranked hypothesis shortlist](docs/REVIEW-08E91DAD-20261025.md) · [Review run card](docs/run-card-08e91dad.json). Read the preserved [full standing prompt](#full-project-brief) every session.

> **Latest repository safety review (2026-10-25, DAA237A4): no new TIFF generated; OK TO SUBMIT: NO.** Fixed the shared novelty gate to require final-dot rank correlation as well as surface correlation and dot overlap. Existing S16 TIFF/ZIP independently reverified against pinned sample/catalogue; research downloads only. [Three-pass audit, four conditional hypotheses, sources and blockers](docs/REVIEW-DAA237A4-20261025.md) · [Review run card](docs/run-card-DAA237A4.json). No geological experiment or weekly slot used.

> **Parallel Session (`S15-SCGF`, branch `arena/605655a6-gemsdoe91`, merged alongside S16-PGRD & S16-PC91): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> 137-feature Förstner subsurface-junction + multi-wavelength (150–900 m) Salem tilt-depth + 2-D deconfounded aquifer-baffle Dual-Specialist Auto-Context (`99`-col provably `B12`/`B19`-invariant Pure-Subsurface specialist): `E1 = 0.235089`, **`E2 = 0.240633`** (`95% CI [0.227931, 0.254026]`), `E3 = 0.232708` **`HOLDOUT-DTI`** (`gems91-hide-recover-v1.0` = `v1.1-nohalo`, `60,988` withheld) and **`0.097940` Blind Off-Catalogue USGS SGMC DTI** (`+0.002180` vs `S14-PTAC E2 = 0.095760`; `+0.002554` vs `GEMSDOE32 R0 = 0.095386`). Negative under shared readiness gates (`0.240633 < 0.267782 S14-PTAC`; literal 3-px lattice overlap `99.811%`, vs `44.82%` on `GEMSDOE32 R0`); zero weekly slots spent (`slots_used = 0`).
> [Download GeoTIFF](docs/downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif) (`sha256: 08933227…ca3a1`) · [Single-TIFF ZIP](docs/downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.zip) · [Audit](docs/s15-scgf.html) · [Executive summary](docs/s15-scgf-executive-summary.html) · [Run card](docs/run-card-S15-SCGF.json) · [Preregistration](docs/HYPOTHESES_S15_SCGF.md) · [3-Pass review](docs/REVIEW-S15-SCGF-20261025.md) · Form note (`90/140`): `S15-SCGF E2: Forstner+multi-scale Salem+baffle dual-AC; HOLDOUT-DTI=0.2406; 44k [0,1] dots`

> **Parallel Session 16B (`S16-PC91`, branch `arena/3b49ef79-gemsdoe91`, merged alongside S16-PGRD): AUTOMATED VERDICT `OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`.**
> Kovesi phase-congruency detector falsified on the comparable holdout: E1 `0.123600` / E2 `0.137450` / E3 `0.174120` HOLDOUT-DTI (`gems91-hide-recover-v1.0`, 60,988 withheld) vs prior best `0.262209`; E3 Rule-1 duplicate-stop (86.00% vs DDVTC), never written. Unique delivered TIF `gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif` (SHA-256 `dfee391717…4f9df6`), triple-gate CERTIFIED + independently re-verified. Zero weekly slots spent.
> [Download](docs/downloads/gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif) · [ZIP](docs/downloads/gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.zip) · [Audit](docs/s16-pc91.html) · [Executive summary](docs/s16-executive-summary.html) · [Run card](docs/run-card-S16PC.json) · [Preregistration](docs/HYPOTHESES_S16PC.md) · [Session report](docs/S16PC_20261025.md) · Form note (69/140): `S16-PC91 phase-congruency monogenic E1 37654d HOLDOUT-DTI 0.1236 v1.0`

> Parallel historical review: [ADFB5EE6 audit](docs/REVIEW-ARENA-ADFB5EE6-20261025.md). Its missing-local-data statements describe that session, not the references restored for this audit.

## Start here every session

**Current review (2026-10-25):** [Arena branch review and run card](docs/REVIEW-ARENA-6FEDEF59-20261025.md). Current result is negative; no fresh TIFF or score was generated. Existing research-only file is explicitly **not approved to submit**.

Read this status, [the full standing brief below](#full-project-brief), [the current review for this branch](docs/REVIEW-08E91DAD-20261025.md), [the integrated parallel review](docs/REVIEW-ARENA-ABB160F7-20261025.md), [the prior active-checkout review (historical snapshot)](docs/REVIEW-ACTIVE-20261025.md), [the three-pass review](docs/REVIEW-S16.md), and [current limitations](LIMITATIONS_AND_NEXT_STEPS.md) before changing the project. **Maximize P(Win)** means protecting scarce slots from unsupported claims. **Own the outcome** means reporting negative results and fixing unsafe tooling.

Historical S16-PGRD material below is a prior-session research artifact, not a new output from this branch. Its stated gate failures remain explicit; do not treat the historical download link as approval to submit. The full standing user brief is preserved below and must be read again each session.

> **OK TO DOWNLOAD: YES — RESEARCH. OK TO SUBMIT: NO.**
> The new S16-PGRD file is computed from pinned magnetic/gravity inputs, not copied from a prior submission. Its format passes automated checks. Its literal registry-uniqueness and scientific-improvement gates do not pass. No human image inspection is required, and no selector may override a duplicate stop.

- **[Download the new, range-safe TIFF](docs/downloads/gems91-s16-pgrd-20261025T040447Z-24d090ad9f42-zeros.tif)**
- [Single-TIFF ZIP](docs/downloads/gems91-s16-pgrd-20261025T040447Z-24d090ad9f42-zeros.zip) · [Project site](https://buffedlizard55-lab.github.io/GEMSDOE91/) · [Executive summary / exact submission guide](docs/executive-summary.html)
- [JSON run card](docs/run-card-S16.json) · [Independent verification](docs/s16/verification.json) · [Every feature canary](docs/s16/canaries.json) · [Per-fold holdout evidence](docs/s16/holdout.json)

**Submission name:** `gems91-s16-pgrd-20261025T040447Z-24d090ad9f42`
**Note (95/140):** `S16-PGRD: magnetic-gravity transfer residual; 37654 new dots. Research negative; do not submit.`
**TIFF SHA-256:** `0564f679035f797b2c279c5da2c013ac65b6a845f95da97fba89490205f846b9`

> **NEW UNIQUE SUBMISSION (this branch):** [Download GeoTIFF](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif) · [Single-TIFF ZIP](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.zip) · [Audit](docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-audit.json) · [Run card](docs/run-card-unique-offcatalogue-damagezone.json)
> **Submission name:** `gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119` · **TIFF SHA-256:** `a5636b10237757cda5de1a7561a0d5f2600479cdd8610226dfd4c1650b66ca11` · **Verdict:** OK TO DOWNLOAD: YES — FORMAT-CERTIFIED · OK TO SUBMIT: NO — RESEARCH NEGATIVE

## Measured result—not a leaderboard prediction

**0.069397 HOLDOUT-DTI**, 95% CI **[0.057510, 0.081676]**, `gems57-pooled-hide-v2`, **60,988 withheld positives**. Whole intersecting fault components are hidden with an 8 km training buffer; fixed evaluation quadrants are label-blind. Only visible faults are masked pixel-exactly. The paired difference against the matched gravity-only control is **−0.004626 HOLDOUT-DTI**, 95% CI **[−0.010725, +0.001161]**, on the same evaluator/population. No improvement is established.

- **One candidate experiment**, stopped on a literal duplicate; no second/third variant and no weekly slot used.
- **16 candidate fields + one control**, checked separately in all four quadrants; maximum symmetric feature-alone AUC **0.576053** (diagnostic, not a DTI score). Passing a canary is not proof of no leakage.
- **37,654 unit dots**, separation >3 px; all **12,279,160** TIFF cells finite in `[0,1]`, no nodata tag; single-band float32; actual sample CRS/shape/full affine match. These are engineering measurements, not score claims.
- Preplacement: **89 indexed entries attempted**, missing entries explicitly UNVERIFIED; maximum measured absolute Spearman **0.038236**. Final checks stopped at reference **27** with **100%** directed 3 px overlap against the frozen lattice; **62** entries untested after the stop. Different bytes do not establish protocol uniqueness.
- `ORGANIZER-CONFIRMED: null`. Current best live score, eligibility and weekly allowance were not authenticated.

## Why the reported GEMSDOE32 result is not a recipe

[Measured source/geometry audit](docs/s16/gems32-forensics.json) · [Pinned source register](docs/s16/sources.json).

The supplied **0.2778 is an unverified user report**, not an organizer receipt. GEMSDOE32's pinned page explicitly calls its artifact UNSCORED. What we reproduced from bytes: the 37,654-dot result is exactly its 40,199-dot base with 2,545 dots ≤200 m from the catalogue removed—no additions. Its median nearest-neighbor spacing is 3 px, not evidence for a universal optimum or a >300 m catalogue collar.

Under the requested metric, `DTI = T / [0.2T + 0.2(S−M) + 0.8|G|]`. Removing unmatched low-credit mass can improve DTI while retaining max-kernel truth coverage. **T and M are different quantities**, and a dot can cover several truth cells. This is a plausible explanation, not causal proof of a hidden score. Beating 0.2778 is possible in principle but not demonstrated by this experiment. The prompt's **0.4413** and **0.3195** are conflicting unverified live-leaderboard claims here, not promotion thresholds.

We also verified that the advertised GEMSDOE32 ZIP snapshot contains an empty ZIP member, not a TIFF. Our new ZIP is unpacked and its TIFF bytes checked automatically.

## A protocol conflict that cannot be solved by better modeling

The frozen registry lattice covers **99.8713%** of the valid footprint within 3 px; only **6,649** cells remain. Any 37,654-dot binary result must therefore overlap it by at least **82.34%**, even ignoring spacing. The protocol requires at most **70%**. [Reproducible capacity-bound receipt](docs/s16/registry-feasibility.json).

We did not drop the dense reference, substitute symmetric overlap, add anti-registry noise, invent a lane assignment, or waive the rule. A genuinely protocol-unique candidate at this budget is blocked by the stated constraints. This negative is downloadable, **not approved for submission**.

## Science and reproducibility

[Four ranked hypotheses, preregistered before implementation](docs/HYPOTHESES_S16.md). The tested magnetic–gravity transfer-residual lane follows a previously deferred idea but is newly implemented in this checkout. No fleet-wide method novelty is claimed. The named non-fault mimic is an unaltered granite–carbonate contact; lava remanence and survey seams are additional confounders. Fault hypotheses are not confirmed geothermal vents.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Restore only ignored, SHA-pinned reference data needed for file validation:
.venv/bin/python scripts/restore_data.py --only sample_submission,existing_faults
.venv/bin/python generate_submission.py --with-data
.venv/bin/python -m pytest
.venv/bin/python scripts/check_artifact_policy.py
.venv/bin/python scripts/render_portal.py
```

`generate_submission.py` defaults to verification. Its `--run` path only runs the preregistered experiment if it has not already been recorded; it does not regenerate candidates after a duplicate stop or consume competition slots. The inherited version that overwrote `data/official/existing_faults.tif` with fake labels was removed. The placeholder-evidence GEOD recovery entry point is blocked.

Scientific scoring/writing uses the **unchanged pinned shared template**, not a private fork. Source/input hashes, all bootstrap terms and execution logs are retained in `docs/s16/` and `evidence/s16_execution.log`. A separate legacy evaluator now defaults to no hidden-truth halo deletion and fails closed on missing registry/nonfinite canary inputs; its old mode requires explicit opt-in for historical reproduction.

## Source feed and access limits

- [Full fleet GitHub snapshot inventory](docs/fleet-audit.csv) and [supplied result claims](docs/reported-results.csv). Public owner text is not an organizer score receipt.
- Official reference notebook fetched from [DrivenData's repository](https://github.com/drivendataorg/gems-prize-reference-solution). It supplies a U-Net/Tversky-loss example, **not** an authenticated distance-weighted scorer.
- Real competition inputs were restored from existing hash-pinned GitHub mirrors. Raw data/caches remain ignored and are not published. Hash identity is not a data-rights attestation.
- The official DrivenData web pages, USGS, NLR and GDR leads were not fetched/authenticated in the recorded source audit. No authenticated submission-page receipt, live slot allowance, hidden truth or complete private registry is available. No new external-data hypothesis is called viable without access.
- Daily Actions refresh the bounded GitHub source feed into an artifact, not the organizer leaderboard. Pages remains in legacy main-root mode: it publishes committed snapshots, not those scheduled refresh artifacts. Changing publisher mode was denied by GitHub (403: Resource not accessible by integration). The GitHub connection needs Pages-settings permission before daily feed auto-publication can be enabled. No workflow trains, searches, picks, or submits candidates.

## Next session priorities

1. Resolve the registry definition/blanket-lattice conflict explicitly; never weaken it silently.
2. Establish the strongest reproducible, comparable incumbent on fixed label-blind folds with paired uncertainty. Quarantine halo-deletion and label-informed-placement results from promotion.
3. Verify official rules, data-use permission, account allowance and score receipts through authorized access; do not request passwords or tokens in chat.
4. Reserve an untouched spatial/geological control to limit adaptive holdout overfitting before any further experiments.

Concurrent main reviews were integrated, including the S15 holdout/final-selector fix and removal of invented selector/slot approval. Their [S15 dated review](docs/REVIEW-ARENA-BB16B6AE-20261025.md) is historical secondary evidence, not a fresh S16 external-page fetch or a score receipt. Its missing-input state does not describe the restored S16 inputs. The subsequent [full-grid audit](docs/REVIEW-C6BFB72B-20261025.md), its 11 edge-case tests, and S15 prerequisite/registry fixes are also preserved. The later [CED91 review](docs/REVIEW-ACTIVE-0A96AA96-20261025.md) and its [dated portal](docs/review-0a96aa96-home.html) remain accessible as history, not a competing current-candidate recommendation. The [DZ-EDGE retirement review](docs/REVIEW-ACTIVE-6FEB36E3-20261025.md), its frozen [portal snapshot](docs/archive-review-6feb36e3.html), and its builder quarantine are also integrated. A later [parallel H1 landing](docs/archive-h1-landing.html) and its three raster/ZIP artifacts are preserved as quarantined research. They arrived after S16’s frozen registry and were not compared after its duplicate stop.

[Prior README, preserved as historical and unverified](docs/archive/README-before-S16.md). [Detailed limitations and next steps](LIMITATIONS_AND_NEXT_STEPS.md).

<a id="full-project-brief"></a>

## Original user project brief — preserved standing text and supplied updates

<details>
<summary>Preserved standing user prompt; read at every session start</summary>

The text below is the user's requirements and supplied claims, not independent evidence. Conflicting leaderboard claims and the missing single-method paragraph are retained and flagged above. Current supplied GEMSDOE89/90 values are included. This is the previously preserved full standing brief with those updates; byte-for-byte identity to the latest long message has not been established.

Review the repo.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION.  DO NOT COPY A PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.  BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION.  IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt.  Read the entire prompt.  A lot of sites mention inspection only and a human inspector, but the inspection needs to be done through the project and needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall within 3 px of one registry raster's dots, you have drifted into another lane: log it as a duplicate and stop. Check this on the surface before placement AND on the final dots.

2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_[holdout.py](http://holdout.py) and submission_[writer.py](http://writer.py). Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it once in the template and report it; never keep a private fork.

3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written as a score.

4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above [0.90] means leakage until proven otherwise.

5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name + note of at most 140 characters; verdict promote / negative. Negative results are deliverables.

6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real slot is a separate selector step, within the weekly cap shown on the submission page.

The following sites should serve as a starting point for understanding how to generate TIF submissions.  These websites are researched, and tested and have generated TIF submissions.  But we need to generate high scoring submissions.

Here are the results from submissions into the competition, separated by ....:

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

WE NEED TO STUDY, ANALYZE, AND UNDERSTAND THE HIGHEST SCORE FROM THE GEMDOE SITE WHERE THE SUBMISSION TIF IS DOWNLOADED FROM WHICH IS THE FOLLOWING:

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

Why and how did this get the highest score and are we able to generate a submission that scores higher than 0.2778?

Answer the question using Phd level experience, knowledge, and judgement. Then use the answer to generate a unique TIF submission into the competition.  Must be unique submission unlike any within the GEMSDOE sites above.  Verify working line by line no hallucinations.

Current competition leaderboard GEMSDOE high score:

0.4413

[https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html)

gems-submission-20260925T001403Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/6GEMSDOE/](https://buffedlizard55-lab.github.io/6GEMSDOE/)

gems6_hgb88-topk03_33cec71ff0: 0.0286

....

[https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html)

pindrop-v4-nodes-20260925T152420Z-f347b70daa: 0.1193

pindrop-v4-discovery-20260925T152423Z-37f9d5b855: 0.0830

pindrop-v4-ridge-20260925T152422Z-4e03fc9705: 0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html)

gemsdoe2-dual-family-union-20260925T160406Z-f68e590f: 0.1560

....

[https://buffedlizard55-lab.github.io/GEMSDOE4/](https://buffedlizard55-lab.github.io/GEMSDOE4/)

gems-submission-20260926T163915Z-237f0063: 0.0343

....

[https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html)

gems-submission-20260926T175114Z-7f00890a: 0.1563

....

[https://buffedlizard55-lab.github.io/7GEMSDOE/](https://buffedlizard55-lab.github.io/7GEMSDOE/)

lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461

....

[https://buffedlizard55-lab.github.io/8GEMSDOE/](https://buffedlizard55-lab.github.io/8GEMSDOE/)

Hedge-v2_submission: 0.1563

....

[https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html)

2314b599: 0.0107

....

[https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html)

gems-structural-area06-v1: 0.0202

....

[https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html)

r7-nms3-dem10-scarp_0c9199f14e62:0.1294

r7-nms3-dem10-scarp_0c9199f14e62_allfinite:0.1294

....

[https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html)

gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782

....

[https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html)

GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f: 0.0020

....

[https://buffedlizard55-lab.github.io/17GEMSDOE/](https://buffedlizard55-lab.github.io/17GEMSDOE/)

17GEMSDOE_F-ensemble-2pct_20260930T050626Z:0.0187

....

[https://buffedlizard55-lab.github.io/18GEMSDOE/](https://buffedlizard55-lab.github.io/18GEMSDOE/)

H19-C_20260930T212401Z_c11e495e: 0.0297

....

[https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html)

h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan: 0.1894

h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan: 0.1922

....

[https://buffedlizard55-lab.github.io/GEMSDOE10/](https://buffedlizard55-lab.github.io/GEMSDOE10/)

h16-continuation-20260927T065521077735Z-3431b83c7c: 0.0461

h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686: 0.0921

H25-ctx-ridge-20260927T232947704150Z-6452ae1d00: 0.1280

h28-dotted-ridge-20260928T020256236880Z-6452ae1d00: 0.1839

....

[https://buffedlizard55-lab.github.io/13GEMSDOE/](https://buffedlizard55-lab.github.io/13GEMSDOE/)

20261001_r13-lattice-s5_v2_nan-outside:0.0904

....

[https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html)

h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan: 0.1855

h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan: 0.0976

h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan: 0.0360

....

[https://buffedlizard55-lab.github.io/GEMSDOE21/](https://buffedlizard55-lab.github.io/GEMSDOE21/)

h19-4-reference-20260930-691e4dfa: 0.1894

....

[https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html)

h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan: 0.1890

h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan: 0.1859

....

[https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html)

h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan: 0.1002

h23-b-dti-optimal-emission-10pct-20261002-86176698-nan: 0.0748

....

[https://buffedlizard55-lab.github.io/GEMSDOE23/](https://buffedlizard55-lab.github.io/GEMSDOE23/)

h30-arrangement-matched-habitat-20261002-0d4e02e8-nan: 0.1352

....

[https://buffedlizard55-lab.github.io/GEMSDOE24/](https://buffedlizard55-lab.github.io/GEMSDOE24/)

h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan: 0.2477

....

[https://buffedlizard55-lab.github.io/GEMSDOE25/](https://buffedlizard55-lab.github.io/GEMSDOE25/)

dotted-h19-5-d2-8-20261002-e56ea318af89-nan: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE26/](https://buffedlizard55-lab.github.io/GEMSDOE26/)

dilcond-oof-v1-20261003-47629f496133-nan: 0.1223

....

[https://buffedlizard55-lab.github.io/GEMSDOE27/](https://buffedlizard55-lab.github.io/GEMSDOE27/)

topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan: 0.2449

....

[https://buffedlizard55-lab.github.io/GEMSDOE30/](https://buffedlizard55-lab.github.io/GEMSDOE30/)

d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca: 0.2600

....

[https://buffedlizard55-lab.github.io/GEMSDOE31/docs/](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/)

h27-4-solo-d28-20261004-8acb75e1-nan:0.2708

....

[https://buffedlizard55-lab.github.io/GEMSDOE33/](https://buffedlizard55-lab.github.io/GEMSDOE33/)

h33d-analog-tip-stepover-r30-20261004-cb490425926e: 0.2632

....

[https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html)

h34-scatter-q50-arr-matched-20261004T223317Z: 0.0778

....

[https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html)

h35-06-aaa86efb25-20261004T225420098147Z-candidate: 0.0418

....

[https://buffedlizard55-lab.github.io/GEMSDOE36/docs/](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/)

anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros: 0.2750

....

[https://buffedlizard55-lab.github.io/GEMSDOE37/](https://buffedlizard55-lab.github.io/GEMSDOE37/)

h6-physics-dotted-80k-20261005T055000Z-0bef9211631c: 0.1193

....

[https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html)

D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero: 0.0763

....

[https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html)

xscale-worm-persistence-20261006T000541Z-nan: 0.0581

....

[https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html)

sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan: 0.0424

....

[https://buffedlizard55-lab.github.io/GEMSDOE45/](https://buffedlizard55-lab.github.io/GEMSDOE45/)

h51-km-faultzone-20261006-zeros: 0.0106

....

[https://buffedlizard55-lab.github.io/GEMSDOE49/](https://buffedlizard55-lab.github.io/GEMSDOE49/)

gate_ortho_w0.25-40k-20261006T213721Z-nan: 0.2376

....

[https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html)

h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778

....

[https://buffedlizard55-lab.github.io/GEMSDOE28/](https://buffedlizard55-lab.github.io/GEMSDOE28/)

h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan: 0.2708

h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan: 0.2649

h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan: 0.2710

h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan: 0.2707

....

[https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html)

efd28-repro-20261003-1cc7dc534d51-nan: 0.2600

repo-c0-habitat-emission-20261003-a4d439b07426-nan: 0.0041

sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan: 0.0512

wormrank-d28-20261003-59dcaf6dd11d-zeros:0.2560

wormsurv-filter-20261003-921f10960d6e-zeros: 0.0532

xfit-c0-habitat-20261003-ca879db0089a-zeros:0.0439

xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros: 0.0356

....

[https://buffedlizard55-lab.github.io/GEMSDOE46/](https://buffedlizard55-lab.github.io/GEMSDOE46/)

r11f-scarp-radiometric-fusion-00e049b51218-zeros:0.1589

r12-scarp-rad-concordance-23e807e2de9f-zeros: 0.0843

....

[https://buffedlizard55-lab.github.io/GEMSDOE39/](https://buffedlizard55-lab.github.io/GEMSDOE39/)

h40-e-disc-h40e-30k-zeros: 0.0339

....

[https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html)

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1: 0.0355

h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard: 0.0397

h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros: 0.0984

....

[https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE41/docs/index.html)

h42-submission-primary: 0.0245

....

[https://buffedlizard55-lab.github.io/GEMSDOE44/docs/](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/)

h46-twostageAB_20261006T160000Z_b0cfe956-zeros: 0.0715

....

[https://buffedlizard55-lab.github.io/GEMSDOE47/](https://buffedlizard55-lab.github.io/GEMSDOE47/)

h60-lidarscarp-s2p0-20261007-nanoutside: 0.0430

....

[https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html)

h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8: 0.2296

....

[https://buffedlizard55-lab.github.io/GEMSDOE50/](https://buffedlizard55-lab.github.io/GEMSDOE50/)

h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite: 0.0764

....

[https://buffedlizard55-lab.github.io/GEMSDOE51/](https://buffedlizard55-lab.github.io/GEMSDOE51/)

h53-twostage-20261008T040951Z-9a0b32c871: 0.1047

....

[https://buffedlizard55-lab.github.io/GEMSDOE52/](https://buffedlizard55-lab.github.io/GEMSDOE52/)

h97b-candidate: 0.0856

....

[https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html)

h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros: 0.0159

....

[https://buffedlizard55-lab.github.io/GEMSDOE54/docs/](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)

h54c-manifest-edge-20261009T025732Z-73454bc5:0.0449

....

[https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html)

tensor_full-n16000-sep3-20261009T211747Z-nan: 0.0290

....

[https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html)

h56-final-dotted-ridge-d2p8-20261009T190421Z:0.0658

....

[https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html)

h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros: 0.0254

....

[https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html)

ml-binary-ridge-20261012T000000Z: 0.0180

....

[https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html)

h59j-coherence-consensus-dotted-20261011T043000Z: 0.0499

....

[https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html)

h73-chi-coherent-corridor-12000-20261011T195818Z-zeros: 0.0351

....

[https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html)

h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros: 0.0009

h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros:0.0751

....

[https://buffedlizard55-lab.github.io/62GEMSDOE/](https://buffedlizard55-lab.github.io/62GEMSDOE/)

datum-lahontan-strain-gauge-defensible-440dots-zeros: 0.0000

....

[https://buffedlizard55-lab.github.io/GEMSDOE63/](https://buffedlizard55-lab.github.io/GEMSDOE63/)

cvarlw-thin-s3p17-54864-20261011T220606Z-c58f60c4-zeros: 0.2303

....

[https://buffedlizard55-lab.github.io/GEMSDOE64/](https://buffedlizard55-lab.github.io/GEMSDOE64/)

h64-lidar-scarp-cv-20261011T220000Z:0.0383

....

[https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE65/docs/index.html)

sar-em-propensity-half-20261011T223500Z-5e4660cd-zeros:0.0431

....

[https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html](https://buffedlizard55-lab.github.io/GEMSDOE66/docs/index.html)

gems66-lidar03-cvretrain-reliefdecile-37654dots-20261020T190152Z-zeros:0.1152

....

[https://buffedlizard55-lab.github.io/GEMSDOE67/](https://buffedlizard55-lab.github.io/GEMSDOE67/)

h67a-orientip-lane-29447dots-20261012T021226Z-allfinite:0.0356

ovtr-ml-cover-tau3p0-20261012-nan:0.1426

....

[https://buffedlizard55-lab.github.io/GEMSDOE68/](https://buffedlizard55-lab.github.io/GEMSDOE68/)

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-nan:0.0437

gems68-autoctx-s3-strands-35000dots-20261020T210000Z-849a0f04-zeros: 0.0437

....

[https://buffedlizard55-lab.github.io/GEMSDOE69/](https://buffedlizard55-lab.github.io/GEMSDOE69/)

h69-joint-relayramp-pullapart-38669-20261020T201504Z-f29b6df5:0.0053

....

[https://buffedlizard55-lab.github.io/GEMSDOE70/](https://buffedlizard55-lab.github.io/GEMSDOE70/)

gems70-p5-dual-submod300-oof38k-20261020:0.2478

....

[https://buffedlizard55-lab.github.io/GEMSDOE71/](https://buffedlizard55-lab.github.io/GEMSDOE71/)

gems71-hydro-conduit-38800-20261020T120000Z-zeros: 0.0558

....

[https://buffedlizard55-lab.github.io/GEMSDOE72/](https://buffedlizard55-lab.github.io/GEMSDOE72/)

gemsdoe72-h72-1-sgmc-offcatalogue-20261020T195456Z-6e6525e5-zeros: 0.0492

....

[https://buffedlizard55-lab.github.io/GEMSDOE73/](https://buffedlizard55-lab.github.io/GEMSDOE73/)

gems73-h73-mcsc-seamfree-blakely-37654dots-20261021T073716Z-b27ac445-zeros: 0.1917

....

[https://buffedlizard55-lab.github.io/GEMSDOE74/](https://buffedlizard55-lab.github.io/GEMSDOE74/)

gemsdoe74-triregime-radon-piedmont-37654-20261021T051000Z-zeros:0.0669

....

[https://buffedlizard55-lab.github.io/GEMSDOE75/](https://buffedlizard55-lab.github.io/GEMSDOE75/)

gems75-trlt-radon-loco-ridge-20261021-zeros:0.1627

....

[https://buffedlizard55-lab.github.io/GEMSDOE76/](https://buffedlizard55-lab.github.io/GEMSDOE76/)

gems76_h76_3_geotherm_tilt_axial_submod_20261021_zeros:0.1555

gems76-ptcf-tiltworm-submod39k-20261021T034000Z-6316481d-zeros:0.2343

....

[https://buffedlizard55-lab.github.io/GEMSDOE77/](https://buffedlizard55-lab.github.io/GEMSDOE77/)

gems85-h85-edti-collar35-skel-r33-20261021-d97b248e-zeros:0.0964

....

[https://buffedlizard55-lab.github.io/GEMSDOE78/](https://buffedlizard55-lab.github.io/GEMSDOE78/)

gems78-h78sigx-fuse-b5-44090dots-20261022T021932Z-zeros:0.1564

....

[https://buffedlizard55-lab.github.io/GEMSDOE79/](https://buffedlizard55-lab.github.io/GEMSDOE79/)

gems79-tilt-ring-100000dots-20261022T212135Z-50a5d7498c71-zeros:0.0005

....

[https://buffedlizard55-lab.github.io/GEMSDOE80/](https://buffedlizard55-lab.github.io/GEMSDOE80/)

gemsdoe80-h80g-choquet-tworegime-20261022T000000Z-zeros:0.0943

....

[https://buffedlizard55-lab.github.io/GEMSDOE81/](https://buffedlizard55-lab.github.io/GEMSDOE81/)

gems81-cont-poisson44090-buf2-20261021T233115Z-42223e10-zeros:0.0041

....

[https://buffedlizard55-lab.github.io/GEMSDOE82/](https://buffedlizard55-lab.github.io/GEMSDOE82/)

gemsdoe82-h82-submodular-punoisyor-20261021T235456Z-fe137199-zeros:0.1886

....

[https://buffedlizard55-lab.github.io/GEMSDOE83/](https://buffedlizard55-lab.github.io/GEMSDOE83/)

gems83-h83-gvcd-dink300-37654dots-20261021-1a373694-zeros:0.0573

....

[https://buffedlizard55-lab.github.io/GEMSDOE84/](https://buffedlizard55-lab.github.io/GEMSDOE84/)

gems84-h84-kthm-tworegime-58000px-20261022T235900Z-zeros:0.0132

....

[https://buffedlizard55-lab.github.io/GEMSDOE85/](https://buffedlizard55-lab.github.io/GEMSDOE85/)

gemsdoe85-hjcd-ventbridge-submod-zeros: 0.1110

....

[https://buffedlizard55-lab.github.io/GEMSDOE86/](https://buffedlizard55-lab.github.io/GEMSDOE86/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE87/](https://buffedlizard55-lab.github.io/GEMSDOE87/)

h87-h87-cmgep-20261022T060000Z-8f394f43:0.0500

....

[https://buffedlizard55-lab.github.io/GEMSDOE88/](https://buffedlizard55-lab.github.io/GEMSDOE88/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE89/](https://buffedlizard55-lab.github.io/GEMSDOE89/)

gemsdoe89-bh-rtp-habc-20261024-d7e1507c-zeros:0.0301

....

[https://buffedlizard55-lab.github.io/GEMSDOE90/](https://buffedlizard55-lab.github.io/GEMSDOE90/)

gems90-cnc-35000dots-20261024T084324Z:0.0749

....

[https://buffedlizard55-lab.github.io/GEMSDOE91/](https://buffedlizard55-lab.github.io/GEMSDOE91/)

:

....

[https://buffedlizard55-lab.github.io/GEMSDOE92/](https://buffedlizard55-lab.github.io/GEMSDOE92/)

:

....

I think it makes sense that in order for a submission to be validated that it needs to pass certain high scoring validation gates before confirming whether a file is unique and can be submitted for scoring.

The following is the leaderboard for the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)

See below for more links and information related to the competition:

[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution)

[https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)

[https://gbcge.org/current-projects/ingenious/](https://gbcge.org/current-projects/ingenious/)

[https://epsg.io/32611](https://epsg.io/32611)

[https://en.wikipedia.org/wiki/Tversky_index](https://en.wikipedia.org/wiki/Tversky_index)

We need to quickly look at the results and results from the GEMSDOE websites above.

Before implementing, generate 3–5 candidate geological hypotheses we haven't tried yet, each naming: the specific layer(s) involved, the physical signature being targeted (e.g., an edge-detection or curvature transform), why it should catch a fault missing from the USGS/INGENIOUS catalogue rather than one already in it, and how it differs from anything already implemented in this repo. Rank them by expected DTI improvement and implementation cost. Validate the top candidate on our spatially-blocked holdout set before touching a weekly submission slot — do not spend a submission slot on an idea that hasn't beaten the current holdout best. If a candidate can't be validated without new external data, name the specific free, official source needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We have a good understanding of how our hypothesis, methodology, calculations, analysis are done so we should be able to figure out a way to score higher on the leaderboard using previous results and scoring that we have across the sites listed above.  We need to come up with distinct and unique strategies to score higher in this competition leaderboard.  We need to start doing heavy and deep research into the part of the project that matters the most, which is the scientific discovery of geothermal vents.  We should store all of our information and knowledge that we can gather from official verified sources.  This will serve as a starting point for other projects as well.  We need to think outside the box but still be grounded in proper scientific research, we are ultimately aiming for a top prize that many others are competing for.  So it's important to be contrarian but be smart about it.  We need to find sources of data that others are over looking or areas of the project when it comes to geothermal vents.  We need to do deep research and critical thinking and come up with new hypothesis to test.

0.3195	is the highest score right now so we need to design a new strategy, research, testing, analyzing, and generating submission system than the current website.  It should be unique, take unique approaches to generating a submission that can score higher than 0.3195.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use.  It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

Review the repo.

The following is taken from the Arena AI team and I think it makes a good point on building a successful project, so let's keep the Core Values and Own the Outcome as a focal point when building, developing, researching, suggesting upgrades, and implementing the work.

Our Core Values

Maximize P(Win)

"Maximize the Probability of Winning": our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). "Maximize P(Win)" frees us from constraints and clarifies that we must put Arena first.

Own the Outcome

We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

We need to focus on being able to generate a submission into the competition.

The site should be able to generate a TIF file that is required for submission.  It should be as easy as download to click a File to submit into the competition.  This needs to be in the executive summary or the very beginning of the site.  it should be obvious when you visit the site.

I tried to submit the document that i downloaded from the site but it returned this error on the submission form:

"Predicted values must be in range [0, 1]"

Also we need to give it a unique name and A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Here is the submission page when i click submit file

New submission

File to submitNo file chosen

You can submit a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF, with your predictions. It must match the submission format's CRS, shape, and geotransform. You may wish to review the competition rules first.

Note (optional)

A short comment to help you or your team tell submissions apart later e.g. clustering with k=25

Create a executive summary subpage that explains exactly how to make a submission into the contest.

Work on the next steps from the previous sessions first.

The goal of this project is to place top of the leaderboard in this competition.  The following is the competition:

[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)

We need to create a project that can compete and place top of the leaderboard.  We need to understand the problem, collect all the data and organize it into a clean easily auditable table with official verified links for manual verification.

This is the guidelines we need to follow.[https://www.drivendata.org/competitions/306/competition-doe-gems/](https://www.drivendata.org/competitions/306/competition-doe-gems/)

Get familiar with the problem through the overview and problem description,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/). You might also want to reference additional resources available on the about page,[https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/).

Download the data from the data,[https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), tab.

Create and train your own model. This reference solution,[https://github.com/drivendataorg/gems-prize-reference-solution](https://github.com/drivendataorg/gems-prize-reference-solution) implements a simple approach.

Use your model to generate predictions that match the submission format.

Tell me what are you limitations and what you need access to during this project.  We will need to find free publicly available sources and data from official and verified sources if we are to use 3rd party or external data.

this pdf outlines how submissions must be entered into the competition.

[https://docs.nlr.gov/docs/fy26osti/96647.pdf](https://docs.nlr.gov/docs/fy26osti/96647.pdf)

You must be able to do your own research, deep research, scientific literature research and organize the knowledge so that we can critically think through the problem and generate a solution through scientific and free publicly available information.  this must be done autonomously and must be constantly reviewed and improved upon.  Provide suggestions and improvements and implement them.

❌ No DrivenData auth → cannot auto-download training_features.tif, labels.tif, sample_submission.tif, 1m_DEM_links.csv from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (verified redirect to login)

See below for links from the above site.  See attached files for links from the above site.

[https://gdr.openei.org/submissions/1391](https://gdr.openei.org/submissions/1391)

Download competition data from [https://www.drivendata.org/competitions/306/competition-doe-gems/data/](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (requires login) to data/

See links below for competition data:

[https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)

[https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)

[https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)

[https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)

[https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Site creation

Create a github page for this repo that has clean ui, user friendly, simple and easy to use.  It should be organized and clean.

It should include all relevant information in an easy to read format with official verified links as sources for review.  Work line by line verify everything no hallucinations.

**The single remaining blocker to training is data placement**: run `bash scripts/download_competition_data.sh` on any unrestricted machine into `data/`, then `python scripts/prepare_data.py` — after that the full train→inference→validate pipeline is ready to run (GPU needed for training; metric/losses/validation all verified working here on CPU).

you need to complete the above task by yourself.  Work line by line verifying from official verified trusted sources, provide links for manual review.  There should be no manual input, work on your own to complete tasks.  Flag any irregularities for review.  No hallucinations.

Verify no hallucinations.

The goal of this project is to get a full list that follow our requirements.  No hallucinations.  Verify line by line.

Run this task through multiple passes.

Pass 1: Implement the task completely and verify the result.

Pass 2: Review your work for bugs, missing requirements, incorrect assumptions, and edge cases. Fix everything you find.

Pass 3: Re-check the entire implementation against the original request. Improve accuracy, reliability, completeness, and code quality. Fix any remaining issues.

Do not stop after the first pass. Each pass must build on the previous one. Before finishing, verify that the final result fully satisfies the original request.  Work line by line verify everything no hallucinations.

Go ahead and create a pull request and then merge the pull request onto the main. Make suggestions for what work still needs to be done and any limitations that is in the way of a successful project.  It should be worked on in this next session or the next session.  Work line by line verify everything no hallucinations.

</details>
