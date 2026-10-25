# HEXFAR91 — hexagonal far-field 18–35 px lattice

## Ranked candidates (this session)

1. **HEXFAR91 (implemented).** Layers: `sample_submission.tif` footprint + `existing_faults.tif`. Signature: Euclidean halo 18–35 px (1.8–3.5 km) with hexagonal stagger (step 13, offset 6). Why off-catalogue: mapped traces are already found; basin-scale relays sit farther out than the 3–10 px collar used previously. Differs from unique-offcatalogue-damagezone (3–10 px square 1 km lattice) and from all HGB/ridge/Euler fusions. Cost: low. Expected DTI vs hide-and-recover catalogue: ~0 (negative control). **Selected.**

2. **Playfair drainage-divide vs fault discordance (not run).** Needs D8 on B12 plus divide extraction; DRN91 already scored 0.166. Cost medium.

3. **K/Th radiometric ratio edge, licence-unchecked GeoDAWN rad stack.** Blocked until licence check. Source: USGS GeoDAWN (https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and).

4. **LiDAR scarp persistence, licence-unchecked.** Blocked.

5. **SGMC-only off-catalogue control emitter.** Already used as a control, not a discovery map.

## Result

HOLDOUT-DTI **0.0** (evaluator `gems91-hide-recover-v1.1-nohalo`, 60,988 withheld, 95% CI [0,0]). Uniqueness pass. Verdict: **negative**. 0 slots spent.

## Why 0.2778 (USER-REPORTED) is higher

GEMSDOE32 R0 is a catalogue-blind ridge network thinned to 37,654 dots with a 2 px collar. Hide-and-recover of *mapped* faults cannot reward far-field lattices. Beating 0.2778 needs a better off-catalogue localiser, not another collar geometry.
