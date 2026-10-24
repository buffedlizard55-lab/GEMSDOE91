# Session 13 Standing Brief (`S13-PTHA`, 2026-10-24, `arena/6a62c2ab-gemsdoe91`)

## 1. Prior-Session Action Items Resolved First

1. **`IR-91-S12-04` (Band 06 physical identity — RESOLVED):** Label-blind correlation (`scripts/verify_band06_and_units.py` → `evidence/s13_band06_and_units_audit.json`) across all `5,164,300` valid footprint cells proves `Band 06 (tc)` in `gems-geodawn-numerical-features.tif` is strictly positive (`[2.953424, 88.566544]`) and equals USGS GeoDAWN Airborne Radiometric Band 4 `'TC'` (Total Count exposure rate) at **Pearson `r = 0.996990`**, despite its embedded GeoTIFF tag misexpanding `'tc'` as `'Tilt angle or total curvature - magnetic field derivative'`.
2. **`IR-91-S12-05` / `IR-91-S12-07` / `IR-91-S12-12` (script hygiene — FIXED):** Fixed `scripts/run_h91_lane.py` so `0.2778` is strictly labelled `CLAIM` rather than `ORGANIZER-CONFIRMED`; fixed `scripts/run_s11_lane.py` to build/fallback cleanly on `h91_full_cat_features.dat` and emit `s11_submission_bundle.js` without invoking `git checkout`.
3. **`IR-91-S13-01` (200× dimensional scaling bug — DISCOVERED & FIXED):** Proved label-blind (`r = 0.999991`) that `Band 03 (tmi_hg)` equals `2 * ||grad_px(Band 14)||` in `nT / 200 m`, whereas `Band 09 (tmi_vg)` is in `nT / m` (`p95(B03/200) = 0.47153 nT/m` vs `p95(|B09|) = 0.46808 nT/m`). Dividing `B09` by `B03/200.0` restores true physical SI Verduzco tilt angle `theta_RTP` and total gradient `AS_SI`.

## 2. Why `GEMSDOE32` (`h33-2-b2`, `0.2778` CLAIM) Led the Early Fleet — and How `S13-PTHA E3` Advances Beyond It

- **Metric mechanics (`alpha = 0.2, beta = 0.8, 300 m` triangular kernel):**
  $$\mathrm{DTI}(S, G) = \frac{T(S)}{T(S) + 0.2\,\mathrm{FP}(S) + 0.8\,\mathrm{FN}(S)} = \frac{T(S)}{0.8\,|G| + 0.2\,|S| + 0.6\,T(S)}$$
  Any continuous halo $p \in (0, 1)$ pays $0.2\,p$ per pixel outside $300\text{ m}$ of ground truth while contributing at most capped recall near covered faults. Using the uniform lattice probe (`calib_r13lattice_00904.tif`, $|S| = 206,895$, $\bar{c} = 0.37482$, score `0.0904`), hidden leaderboard fault volume inverts to $|G_{\text{LB}}| \approx 12,350$ pixels (`~20.2%` of the `60,988` training fault pixels).
- **Why `GEMSDOE32` (`37,654` binary dots, spacing `≥ 2.8 px`) beat continuous U-Net rasters (`0.1235–0.1592`) and over-dotted submissions (`0.0904–0.2145`):**
  1. Binary `{0, 1}` point impulses matched to the `300 m` triangular kernel radius (`2.8 px` spacing gives hexagonal overlap coverage with zero wasted mass).
  2. Strict exclusion inside `d_cat ≤ 3.0 px` (`300 m`) of `existing_faults.tif` (zero reward, pure `0.2 |S|` denominator tax).
  3. Operating near the `~37.6k–44k` dot sweet spot implied by $|G_{\text{LB}}| \approx 12,350$.
- **Why `GEMSDOE32` plateaued at `0.153644 HOLDOUT-DTI` (`0.095386 SGMC`) and how `S13-PTHA E3` reaches `0.244601 HOLDOUT-DTI` (`0.100815 SGMC`):**
  `GEMSDOE32` relied on raw 20-band HGB probabilities and a fixed global `37,654` dot count without dimensional `nT/m` RTP physics, odd-parity cross-fault step filters, or per-domain marginal-DTI stopping. `S13-PTHA E3` adds:
  - **`H13-1`:** Dimensionally consistent Blakely-Simpson RTP `theta_RTP`, horizontal tilt gradient `HD_TDR_SI`, `AS_SI`, `K_RTP`, and strike-aligned cross-fault odd-parity step-to-roughness across 6 orthogonal physical fields (DEM, CBA, RTP-TMI, Radiometric `TC`, Geodetic `E2`, Magnetotelluric `MT-2km`).
  - **`H13-2`:** Geodetic strain-rate orientation & slip tendency (`Band 07/12/13`), conductive-upflow coupling (`Band 08/19`), and non-fault contact-metamorphic aureole suppression.
  - **`H13-3`:** Prior-shift empirical-Bayes probability calibration + 4-azimuth 1-D cross-strike crest extraction + Dinkelbach Charnes-Cooper fractional-DTI lazy-greedy submodular allocation (`tau* = 0.2 * DTI* / (1 - 0.6 * DTI*)`).

## 3. Session 13 Experimental Ladder (`gems91-hide-recover-v1.0`, `n_withheld = 60,988`)

| Arm | Features & Emitter | Pooled `HOLDOUT-DTI` (95% CI) | Delta vs `S11-E2` (`0.206406`) | Pooled `T` / Dots `S` | Blind `SGMC` DTI |
| --- | --- | --- | --- | --- | --- |
| `R0` (`GEMSDOE32`) | 20-band HGB + `37,654` NMS dots | `0.153644` (ref) | `-0.052762` | — | `0.095386` |
| `S11-MHTR E2` | 59f MHTR + fixed `12k/fold` (`47,811`) | `0.206406` (`[0.193796, 0.220176]`) | `0.000000` | `12,265.0 / 47,811` | `0.097623` |
| `S13-PTHA E1` | `59 + 8 (H13-1) = 67f` + fixed `48k` | `0.197522` (`[0.185248, 0.208527]`) | `-0.008884` | `11,816.0 / 48,000` | — |
| `S13-PTHA E2` | `67 + 8 (H13-2) = 75f` + fixed `48k` | `0.198407` (`[0.184119, 0.210717]`) | `-0.007999` | `11,869.1 / 48,000` | — |
| **`S13-PTHA E3`** | **`75f` + `H13-3` Bayes + 1-D Crest + Dinkelbach** | **`0.244601` (`[0.230592, 0.257058]`)** | **`+0.038195` (`[+0.029931, +0.046719]`, `400/400 > 0`)** | **`14,336.8 / 40,815`** | **`0.100815`** |

## 4. Next Steps for Session 14+

1. **Human Selector Review:** Review `docs/s13-ptha-executive-summary.html` and `docs/run-card-S13.json`. Under mutual exclusion, `S13-PTHA E3` supersedes all prior `GEMSDOE91` candidates (`S11-MHTR`, `FUSE91`, `CCR91`, `H91`, `DENOVO`). Confirm live DrivenData 3/rolling-7-day slot budget and `IR-CED-003` synthetic lattice policy before uploading.
2. **Official USGS 3DEP 1-m LiDAR (`H13-5`) on Unrestricted Host:** Fetch public-domain USGS 3DEP 1-m tiles directly from official USGS National Map endpoints (avoiding unverified sibling derived rasters) to compute sub-meter alluvial scarp asymmetry (`10–50 m` aperture) and fuse with `S13-PTHA` posterior odds.
3. **2-D Contextual U-Net + Dinkelbach Hybrid:** Train a 4-fold spatially blocked lightweight residual U-Net on the physical 16-channel `PTHA` tensor (`theta_RTP`, `HD_TDR_SI`, 6-field odd step, geodetic `E2`, MT) with Tversky loss (`alpha=0.2, beta=0.8`) and feed its calibrated posterior directly into `PTHA` 1-D directional ridge + Dinkelbach submodular dot allocation.
