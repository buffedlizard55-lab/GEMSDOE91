# S30-VCSE — ranked geological hypotheses (2026-10-31)

Five new, mechanism-level hypotheses for off-catalogue (hidden) fault discovery
in the GEMS geothermal province. Each states the specific layers/transform, why
it catches faults the catalogue family misses, how it differs from prior repo
work, its mimicking non-fault process, and is ranked by expected HOLDOUT-DTI
improvement over the registered bar (0.159482) per unit cost.

Ranking is our MODEL expectation, never a score. The top hypothesis was
validated on the spatially-blocked holdout BEFORE any submission slot
(preregistered run card: `docs/s30-vcse/run-card.json`).

| Rank | Hypothesis | Physical signature transform | Why it catches off-catalogue faults | Difference from repo work | Mimicking non-fault process + gate | Expected HOLDOUT-DTI improvement (MODEL) | Cost |
|---|---|---|---|---|---|---|---|
| **1 (validated = the run-card lane)** | **B. Vent/alteration + strain concordance strands** | Multi-channel concordance: `geodawn_rad_u8` K/Th/U/TC + `gdr_wellspring` vents + `cond_surf` clay caps + `deq/ieq` seismicity + `geod_shearrate/dilaterate` corridors; CELF placement off-collar | Hydrothermal upflow along permeable strands leaves K-depletion/Th-U-fractionation, conductive caps and warm springs ON the fault — independent of ridge morphology the 0.24–0.28 family dots on | First VCSE lane (this session); prior work placed dots on ridge/edge energy, never on vent-strain concordance | Playa/lake conductivity (saline, K-poor, flat) — gated by basin-floor veto (step/relief ranks) + structural concurrence rule | Highest: the only pattern whose blind SGMC control cleared parent R0 (+28% relative) | 3 experiments (spent) |
| 2 | **C. Differential-depth edges (gravity vs magnetics vs cover steps)** | `iso_grav_anom_hg` ∇ vs `tmi_hg` ∇ disagreement + `depth_to_base_surf`/`cond_surf` steps; edge-coincidence score | Faults displace basement against cover: the gravity–magnetic depth mismatch marks faulted basement offsets that ridge/curvature families miss in cover plains | S27-OSDR used single-depth edges; the *cross-depth disagreement* transform is new | Lithologic contacts (no cover step) — gate: require cover-depth step co-location | Medium-high (S27 pattern generalises) | 1 experiment, all-local features |
| 3 | **D. Shear ∧ dilation strain corridors** | `geod_shearrate × geod_dilaterate` joint exceedance + `eq_n100a15` alignment | Slip on blind faults loads crust: shear+dilation corridors with seismicity alignment trace active strands not yet expressed at surface | Repo used strain channels only as veto features; never as the primary placement field | Magmatic/inflation sources (dilation without shear) — gate: require shear co-exceedance | Medium | 1 experiment |
| 4 | **A. Seismicity-concordance strands** | `deq_n100a15`/`ieq_n100a15` density ridges + `tmi_hg` 2nd-invariant support | Earthquake lineaments mark buried fault slip directly | S22 used seismicity only as context; lineament extraction is new | Swarms/induced seismicity (non-tectonic) — gate: require structural co-location | Medium (AUC canary 0.54–0.61 shows weak solo signal) | 1 experiment |
| 5 | **E. Tip-relay vent bridging** | Graph bridging between vent clusters via cond+rad corridors (tip-stepover geometry, GEMSDOE33-style) | Relays between vent fields localize permeability where strands step over | GEMSDOE33 did tip-stepover on ridges; applying it to vent clusters is new | Scattered springs (no relay structure) — gate: require bidirectional corridor support | Low-medium | 1 experiment |

**Promotion rule (standing):** no weekly submission slot is spent unless the
validated candidate beats the registered holdout best 0.159482 on
`gems57-pooled-hide-v2`. Rank 1 was validated (E1/E2/E3) and did **not** clear
the bar (best 0.052966) → verdict negative, 0 slots. Ranks 2–5 remain
untested; rank 2 is the recommended next experiment (all features already in
the template stack; no external data).
