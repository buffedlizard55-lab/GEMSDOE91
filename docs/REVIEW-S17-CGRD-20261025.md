# Session 17 (`S17-CGRD`) Three-Pass Scientific & Engineering Review — 2026-10-25

- **Repository:** `buffedlizard55-lab/GEMSDOE91`
- **Branch:** `arena/cbdb6e26-gemsdoe91`
- **Preregistration:** [`docs/HYPOTHESES_S17_CGRD.md`](HYPOTHESES_S17_CGRD.md) (SHA-256 `b4318c9c37f473d87a14086d91a642bf518a6b67900e3a0d65d86d678187f09c`)
- **Run Card:** [`docs/run-card-S17-CGRD.json`](run-card-S17-CGRD.json) (`schema_version = "gems91.s17-cgrd.v1"`)
- **Delivered Research GeoTIFF:** [`docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif`](downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif) (`203,212` bytes, SHA-256 `287af6b2df1c34080c55cd1aef9264f30e5e507b152ff31dcb94d13cf6f521a6`)
- **Delivered Single-TIFF ZIP:** [`docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.zip`](downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.zip) (`164,903` bytes, SHA-256 `b3f520731ffe64f0bb4d2967755e399ee3ea34fce92b23bd9b0f5e245c324f8f`)
- **Automated Verdict:** `OK TO DOWNLOAD: YES (Research Only)` · `OK TO SUBMIT: NO` (`verdict = "negative"`, `slots_used = 0`)

---

## 1. Forensic Analysis of `GEMSDOE32` (`0.2778`) & DTI Mechanics

Under the competition Distance-weighted Tversky Index ($\alpha = 0.2, \beta = 0.8$, 300 m triangular kernel $K_{300}$):
$$\text{DTI}(S, G) = \frac{T}{0.2\,T + 0.2\,(S_{\text{tot}} - M) + 0.8\,|G|} = \frac{T}{0.2\,S_{\text{tot}} + 0.2\,(T - M) + 0.8\,|G|}$$
1. Every unit dot within 300 m of $k$ hidden fault pixels contributes up to $k$ units of recall credit $T$ while costing only a single unit of emission mass $S_{\text{tot}}$, whereas every redundant dot inside the 200 m ($\le 2\text{ px}$) collar of already-masked visible catalogue faults (`existing_faults.tif`) earns $T \approx 0$ on hidden segments while paying $+0.2$ in the denominator.
2. Direct byte comparison (`docs/s16/gems32-forensics.json`) proves `GEMSDOE32__h33-2-b2-zeros.tif` (`37,654` dots, SHA-256 `c55bafc4...`) is a strict subset of its `40,199`-dot base with exactly `2,545` near-catalogue dots ($\le 2\text{ px}$) removed (`-0.2 * 2,545 = -509.0` denominator penalty removed).
3. Note on score provenance: `0.2778` is supplied in the project prompt as `ORGANIZER-CONFIRMED`, while `GEMSDOE32`'s public commit snapshot labels the artifact `UNSCORED` and both `0.4413` and `0.3195` are unverified prompt figures (`docs/s16/sources.json`).

---

## 2. Three-Experiment Preregistered Ablation Results (`S17-CGRD`)

| Arm | Features | `B12`/`B19` Blind? | `HOLDOUT-DTI` (`v1.0`, $n=60,988$) | 95% CI (`5 km` block bootstrap) | `HOLDOUT-DTI` (`gems57-pooled-hide-v2`) | Real-Registry 3-px Overlap (42 rasters) |
|---|---:|---|---:|---|---:|---|
| **`E1 · CGRD-PureSubsurface`** | 26 | **YES** (0 bytes read) | `0.083981 HOLDOUT-DTI` | `[0.074440, 0.093453]` | — | $\le 70\%$ (`PASS`) |
| **`E2 · CGRD-CalibratedAutoContext` (Delivered)** | 34 | **YES** (0 bytes read) | **`0.092125 HOLDOUT-DTI`** (`+0.008144` vs `E1`) | `[0.081283, 0.102562]` | **`0.225235 HOLDOUT-DTI`** `[0.197388, 0.252846]` | **`56.06% <= 70.0%` (`PASS`)** |
| **`E3 · CGRD-FullMultiPhysics`** | 53 | NO (includes DEM) | `0.132279 HOLDOUT-DTI` (`+0.048298` vs `E1`) | `[0.121610, 0.142760]` | — | `77.51% > 70.0%` (`STOP` vs `SPID-E3`) |

---

## 3. Three-Pass Verification Summary

- **Pass 1 (Implementation & Execution):** Implemented `src/gems91/cgrd17.py`, `scripts/run_s17_cgrd_lane.py`, and `tests/test_s17_cgrd.py`; executed `E1`, `E2`, `E3` on the restored GeoDAWN and GDR-1391 inputs (`924.77 s` wall clock).
- **Pass 2 (Bug & Edge-Case Review):** Remediated `IR-91-S15-06` (prior-shift calibration of pairwise 2-quadrant Stage-1 sub-folds + held-out quadrant negative exclusion), `IR-91-S15-07` ($\ge 3.2\text{ km}$ regional bowl subtraction), and `IR-91-S17-01` (PR #95 portal overwrite & PR #96 unregistered downloads).
- **Pass 3 (Full Regression & Browser Verification):** Verified `475 passed, 0 failed, 0 skipped` in `pytest`, `PASS` in `check_artifact_policy.py`, `audit_downloads.py`, `verify_s16.py`, `verify_evidence.py`, `verify_current_artifact.py`, and `PASS` in `node tools/browser/smoke.cjs` (Chromium + axe-core WCAG 2.1 AA across 21 pages + mobile `390x844` overflow + SHA-256 download check).
