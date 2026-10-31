# S28 · Ranked hypotheses for finding faults that are *not* in the USGS/INGENIOUS catalogue

Ranking key: **expected DTI gain** (from the metric algebra in `REVIEW.md` §1.2 — gain comes only from
true-positive mass, i.e. recall of the hidden set) and **implementation cost** (compute + data already at
hand). Band names are the official `gems-geodawn-numerical-features.tif` descriptors, verified from the
file's band descriptions this session.

Only **H1** has been tested. The rest are falsifiable proposals, not results.

---

## H1 · CPT-19: catalogue-prior transfer classifier on the official stack — IMPLEMENTED, `promote`

* **Layers** — all 19 official bands; 41 derived layers (robust band score, 400 m context, HG energy,
  detrended-elevation curvature, basin × conductivity). No catalogue-derived layer.
* **Physical signature** — the *joint* expression of a fault: magnetic/gravity horizontal-gradient edges
  (offset of the magnetisation/density interface), topographic curvature (scarp), strain-rate second invariant
  (active deformation), and basin depth (buried basin margin).
* **Why it should catch a fault missing from the catalogue rather than one already in it** — training
  positives are mapped faults, negatives are background ≥800 m away, so the learned function is “what this
  terrain looks like where faults are known”, not “where mapped faults are”. Emission removes every cell
  within 300 m of the catalogue, so the only way a dot survives is on a structure the classifier likes that
  the catalogue does not already contain.
* **Difference from anything already in this repository** — first use of the official 19-band stack
  (previously absent from every workspace) and first supervised transfer model; all prior lanes hand-weighted
  one or two derived bands.
* **Cost** — done: 70 s feature build, ~70 s train + emit.
* **Result** — HOLDOUT-DTI **0.102921** vs **0.042443** for the fleet-style physics control on identical
  geometry (×2.43); leakage canary max AUC 0.7947 < 0.90.

## H2 · Multi-scale structure-tensor coherence (next recommended)

* **Layers** — `det_elev`, `det_elev_slope`, `tc`.
* **Physical signature** — orientation coherence and anisotropy of the topographic gradient, computed at
  300 m and 1 km, plus the *consistency* of that orientation across scales.
* **Why it should catch a missing fault** — under Holocene fan wash and pluvial lake deposits the scarp relief
  collapses, but the residual gradient keeps a coherent strike direction; coherence survives where amplitude
  does not. Curvature magnitude alone is blind to that difference.
* **Difference from the repo** — previous lanes used curvature/scarp *magnitude* (e.g. `curv_det_elev`,
  `det_elev_slope` terciles) and never orientation coherence or cross-scale agreement.
* **Cost** — low: three extra layers, same model, ~15 min.
* **Falsifiable prediction** — improves pooled holdout DTI over H1 at identical emission; if it does not, the
  signature is not where hidden faults are.

## H3 · Vertical-gradient dip-reversal pairing

* **Layers** — `tmi_vg`, `iso_grav_anom_vg`.
* **Physical signature** — coincident polarity reversal of both vertical gradients across a lineament, with
  the two reversals spatially locked within a few hundred metres.
* **Why it should catch a missing fault** — a buried normal fault offsets the density/magnetisation interface,
  which flips the vertical gradient across the fault plane even when the surface trace is displaced down-dip by
  Δx = z·cot(dip) under basin fill — i.e. precisely the faults with no topographic expression and therefore
  absent from a surface-mapped catalogue.
* **Difference from the repo** — earlier lanes snapped to horizontal-gradient crests or projected up-dip from
  `depth_to_base_surf`; none tested the polarity-pairing signature itself.
* **Cost** — medium: needs a sign-locked cross-correlation operator and a lock-width calibration.

## H4 · Data-driven relay / step-over completion

* **Layers** — `tmi_hg`, `iso_grav_anom_hg`, `det_elev_slope`.
* **Physical signature** — orientation, length and spacing statistics learned from the catalogue's own
  segment population, applied to unlinked en-échelon lineaments.
* **Why it should catch a missing fault** — unmapped splays are most often the relay between two mapped
  segments; the geometry of those relays is strongly constrained by the mapped population.
* **Difference from the repo** — S33's `analog-tip-stepover` applied a fixed r = 30 geometric rule; this
  estimates the distribution instead of hard-coding it.
* **Cost** — medium: segment statistics + constrained linking search.

## H5 · Geothermal-conduit conditioning

* **Layers** — `cond_surf`, `depth_to_base_surf`, `geod_2ndinv`, `geod_shearrate`.
* **Physical signature** — high conductivity + deep basin fill + active strain coincident with a lineament.
* **Why it should catch a missing fault** — the prize is a *geothermal* prize, so the withheld fault set may be
  enriched where fluid pathways exist; conditioning on conduit physics could raise precision on the subset that
  matters.
* **Difference from the repo** — GDR-well priors used an external point catalogue; this uses the in-raster
  geophysics.
* **Cost** — low, but the most speculative: the truth may be tectonically unbiased. Ranked last for that reason.

---

## What would make any of these non-viable

1. If the hidden truth is spatially disjoint from the mapped fault population in signature space, no
   catalogue-transfer method (H1, H4, H5) can rank it — only new external data (e.g. USGS 3DEP 1 m lidar
   morphometry, or the full INGENIOUS play-fairway vector set) could help, and those hosts are not reachable
   from this sandbox.
2. If the organizers' hidden truth is a random subset of the *same* mapped catalogue, then the correct strategy
   is the opposite of the nine-site winners' (place dots **on** traces), and the fleet's 0.2778 ceiling would
   already be near-optimal — this is testable only by spending a slot.
3. Any arm whose single-layer canary exceeds AUC 0.90 is leakage until proven otherwise and must not be
   promoted.
