# Ranked geological hypotheses — S30-VCE follow-ups (2026-10-31)

Status: **research proposals with measured priors from the S30-VCE run.** H-VCE-1 (vent-concordant
emission) was tested today and delivered a negative-to-neutral holdout result
(HOLDOUT-DTI 0.0674 [0.0542, 0.0828], paired CI vs its blind control includes 0), while its
SGMC off-catalogue diagnostic (0.0480) trails the champion family (0.0954). The four
hypotheses below are what we have not tried, ranked by **expected DTI improvement on our
hide-and-recover instrument** and implementation cost. Budget for the next session: 3
experiments / 2 h, unchanged. All require only data already pinned in `data/`
(hash-verified 2026-10-31 via `scripts/restore_data.py`), except H-VCE-5 which names its
external source explicitly.

---

## H-VCE-2 — Supervised lineament × vent concordance (top candidate)

- **Rank:** 1 · **Expected ΔHOLDOUT-DTI:** high (target ≥ 0.16, the S25/S27 band) · **Cost:** medium (reuse `scripts/run_s30_vce.py` stage pattern; one HGB OOF arm)
- **Layers:** all 19 `training_features.tif` bands (esp. `tmi_hg`, `iso_grav_anom_hg`, `tc`, `rtp` — the potential-field edge stack the champion family rides) **crossed with** the S30-VCE vent features (`vent_kde`, `vent_corridor`, `alter_kdep`, `cond_cap`).
- **Physical signature:** potential-field edges that are *also* hydrothermal upflow corridors. A basement fault expressed in magnetics/gravity AND capped by a conductive alteration halo is a permeable, geothermally active fault — the exact class the labels target ("structures indicative of geothermal resources", problem description).
- **Why it catches faults missing from the catalogue:** the catalogue was mapped from surface rupture; a covered/blind fault with no fresh scarp is still visible as a magnetic offset plus vent/alteration. The interaction term (edge × vent) is what neither the champion family (edge only) nor S30-VCE (vent only) exploited.
- **How it differs from this repo:** S25-FABRIC used granulometry/phase-lag textures; S27-CVDC used contour–potential discordance; S30-VCE used vent stack alone. None used a supervised edge×vent interaction, and none can match this lane's expected holdout.
- **Negative control:** edge-only arm (champion-family physics, fold-local) and vent-only arm (S30-VCE E2) — the interaction must beat both with paired CI > 0. **Named mimic:** lithologic contacts (intrusion margins, volcanic flow edges) produce magnetic edges without faults; the vent term is the discriminator but alteration halos around intrusions can mimic — use `depth_to_base_surf` and `det_elev` strata as covariates and report by stratum.
- **Data readiness:** READY — all bands pinned and hash-verified locally.

## H-VCE-3 — Earthquake-lineament stepover targeting

- **Rank:** 2 · **Expected Δ:** medium · **Cost:** low-medium
- **Layers:** `deq_n100a15`, `ieq_n100a15` (earthquake density), `geod_2ndinv`, `geod_shearrate`, `geod_dilaterate` (strain tensor), `tmi_hg`/`iso_grav_anom_hg` edges.
- **Physical signature:** seismicity and geodetic strain localize at fault stepovers, tips, and relay ramps — the structurally complex sites where Great Basin hydrothermal systems concentrate (USGS Great Basin structural-discontinuity summaries). Target: edge-network nodes with elevated microseismicity and strain, not the edge lines themselves.
- **Why hidden faults:** a blind fault segment between two mapped strands shows as a seismicity/strain bridge with no catalogue trace; nodes are where experts find missing segments.
- **Difference from repo:** GEMSDOE33's "analog-tip-stepover" placed dots on tip/stepover geometry from the lineament surface alone; this hypothesis conditions on independently measured seismicity + strain, which no repo lane used as an emission driver (S22-XB used strain as a weak feature only).
- **Mimic:** reservoir-induced or crustal seismicity unrelated to faults; geodetic strain noise at station edges. Control: shuffled-strain null (block-permuted strain field) must destroy the gain.
- **Data readiness:** READY (bands pinned).

## H-VCE-4 — Conductivity-cap breach permeability

- **Rank:** 3 · **Expected Δ:** medium-low · **Cost:** low
- **Layers:** `cond_surf`, `depth_to_base_surf`, `tc` (tilt/curvature), radiometric `K`/`Th`/`U`.
- **Physical signature:** a resistive cap (silicified sinter) breached by conductive upflow — i.e., sharp conductivity gradients at cap margins, not conductivity highs themselves. Feature: positive gradient magnitude of `cond_surf` conditioned on shallow `depth_to_base_surf` and K-depletion.
- **Why hidden faults:** cap-breach permeability is fault-controlled; the mapped catalogue misses the through-going fault when the surface expression is only a spring vent + sinter rim.
- **Difference from repo:** SASS2 "xghf-dualhorizon-aniso" used conductivity horizons as a static prior; GEMSDOE32's H32c "mt-claycap-breach" tested a clay-cap breach on the ridge family. This lane isolates the *breach edge* of the supplied conductivity surface as the emission driver and pairs it with the GDR vent set — a different surface from both.
- **Mimic:** saline basin-fill conductors and lithologic conductivity contrasts (playa margins). Control: playa/basin mask via `det_elev` terciles must show the gain is not concentrated in basins.
- **Data readiness:** READY.

## H-VCE-5 — Quaternary-fault slip-tendency corroboration (external data required)

- **Rank:** 4 · **Expected Δ:** medium (mechanism-strong, data-risk) · **Cost:** medium
- **Layers:** USGS 2026 Quaternary fault slip/dilation attribute release (for stress orientation context only) + local `geod_*` strain + `tmi_hg` edges.
- **Physical signature:** fault segments optimally oriented for Andersonian slip in the contemporary extension field carry the hidden, active, geothermal-indicative faults. A candidate edge whose strike is within ~30° of the local extension direction (computed label-blind from the strain tensor) is promoted.
- **Why hidden faults:** active optimally-oriented segments are preferentially Quaternary — exactly the expert-label class.
- **Difference from repo:** GEMSDOE36's "anderson-geothermal-pinn" approached this with a PINN but landed in the same dot family (97.6% duplicate); a label-blind strain-orientation gate on a *unique* emission geography is a different construction. Careful: the USGS release computes attributes **on Quaternary fault segments from the USGS fault database** — rasterizing its traces would leak/reproduce catalogue faults (HYPOTHESES.md 2026-10-30, failure mode 2). Use only the regional stress/strain field derived independently from the supplied `geod_*` bands; treat the USGS release as mechanism context only.
- **Mimic:** paleo-stress vs modern stress inconsistencies; strain-field smoothing artifacts.
- **Data readiness:** NOT FULLY READY — local bands suffice for the label-blind version; the USGS slip/dilation report is free and official (usgs.gov) but cannot be fetched from this sandbox (allowlist). If wanted, the free source is the USGS publications warehouse (search "Quaternary fault slip dilation Great Basin 2026"); verify coverage before use. Propose the local-only variant first.

---

**Selection rule for the next session (unchanged protocol):** run the leakage canaries first;
validate H-VCE-2 on the v3 buffered folds; it must beat the current same-evaluator best
(S27-OSDR E2 = 0.159482 [0.139292, 0.179660]) with paired CI above zero before any weekly
slot is spent. Uniqueness gates (ρ ≤ 0.90, ≤ 70 % dots within 3 px vs every registry raster,
including `data/lane_refs/gemsdoe32-h46-trhv…` and `…h51-ewsp…`) apply at packaging. Negative
results are deliverables.
