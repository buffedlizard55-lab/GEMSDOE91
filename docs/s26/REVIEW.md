# S26 — 2026-10-29: emission-geometry lane on validated FABRIC surface

**Lane:** S26-FABRIC-EMIT (self-assigned H1). **Artefacts:** `gems91-s26-fabric-emit-10pxcap-22163dots-…-zeros.tif` (primary, 22,163 dots, 10 px collar) + 37,654-dot variant; both float32 [0,1] EPSG:32611 3730×3292.

**What we did:** Reused S25-FABRIC E2 validated detector (HOLDOUT-DTI 0.1477 [0.1297,0.1675] vs control 0.1247 Δ+0.023 paired CI>0, v3 label-blind-quadrant 80 px buffer, 60,988 withheld) and changed only emission geometry to 10 px collar + gap-weighted pseudo-surface, spacing 3.05 px, budgets 22,163 (capacity NOT_RULED_OUT) and 37,654. Competitive overlap fell 74.9%→60.2% (passes competitive ≤70%), surface |ρ| 0.13 (passes), lattice 98.1% fails literal but is capacity-forced (any 37k honest raster ≥82.34% must; 22k ≥69.999% minimum with spacing → ~200 dot true limit). Validator passes; catalogue 0 dots.

**Verdict:** `negative` / `ok_to_submit: false` under protocol-literal (lattice blanket), `ok_to_download: true` (research). Selector should use competitive scope per S25 precedent. No slot used. H2–H5 hypotheses preserved for next session.

**Files:** `docs/s26/run-card.json` (S26-FABRIC-EMIT) · `docs/s26/executive-summary.html` · `docs/downloads/gems91-s26-…` · `docs/s26/HYPOTHESES.md` / `preregistration.md`
