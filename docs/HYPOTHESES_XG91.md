# XG91 hypotheses — preregistered before holdout numbers (2026-10-25)

The prompt's "single method paragraph below" was absent. This file is the
session's preregistration, not an organizer lane assignment. No holdout number
existed when these five candidates were written. Only candidate 1 is
implemented, and only with the restored, SHA-256-pinned sponsor stack
(`training_features` `4371c82e…3bc5`).

Every later score must be labelled HOLDOUT-DTI (evaluator, withheld count, 95%
CI) or left unlabelled as a projection. Nothing here is ORGANIZER-CONFIRMED.

## Why the reported 0.2778 is not a recipe

Fetched 2026-10-25 from the GEMSDOE32 page itself
(<https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html>): the file
`h33-h33-2-b2` is described as the 0.2708 base with every dot at
`d(catalogue) <= 2 px` deleted (37,654 dots), and the page says **no organiser
score exists**. The note on that page calls 0.2747 a projection and the file
UNSCORED. The user-reported 0.2778 is therefore not a receipt.

Local geometry, re-hashed this session against the pinned zeros twin
(`c55bafc4…b6fa9`): 37,654 unit dots, 0 dots within 2 px of the catalogue,
median nearest-neighbour spacing 3 px. That geometry is consistent with the
published DTI algebra (α=0.2, β=0.8, 300 m triangular kernel): mass sitting on
mapped faults cannot earn credit on a test set of faults that are absent from
the USGS/INGENIOUS catalogue, and it still pays the false-positive term.
Deleting it can raise DTI if matched credit is kept. That is a mechanism, not
proof that this file scored 0.2778.

The public DrivenData leaderboard, fetched 2026-10-25 from
<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>,
shows rank 1 at **0.4413** (participant xiaofanhu). That page is not a
submission receipt for any file in this repository. The prompt's 0.3195 is
below many current public rows and is not used as a gate. Beating 0.2778 on
the organiser metric is possible in principle — the public board is already
higher — but it is not demonstrated by copying R0.

## Ranked candidates

| Rank | Hypothesis | Layers and signature | Why a catalogue-missing fault | Difference from this repo | Mimic | Cost / data |
|---|---|---|---|---|---|---|
| 1 | **XG91 cross-gradient shadow** | Bands 2 `rtp`, 13 `iso_grav_anom`, 15 `depth_to_base_surf`. Gallardo–Meju cross-gradient parallelism at 200 m and 600 m, sampled up-dip of the contact by `H·cot(55°)`. | USGS/INGENIOUS traces follow surface scarps. A covered normal fault's density/susceptibility contact sits downdip of the buried trace experts can still map from GeoDAWN. | Not DENOVO's geometric-mean edge strength, not CED's centroid shift, not an HGB collapse onto the catalogue. | Buried volcanic-flow edge or basin onlap. | Low. Pinned stack restored and hashed. **Implement.** |
| 2 | Conductivity channel discordant with topographic grain | Band 17 `cond_surf` high-pass linearity whose strike differs by >30° from band 12/19 topographic structure-tensor orientation. | Fluid conduits under playa lack scarps; the catalogue is exposure-biased. | S15 used conductivity inside a large auto-context model. This would be orientation discordance only. | Brine-filled playa channels and irrigation. | Medium. Not run (3-experiment cap; rank 1 first). |
| 3 | Radiometric contact offset from the magnetic contact | Official USGS GeoDAWN K/Th/U or total-count grids, plus bands 3 and 9. | Alteration halos are not fault traces; the structure can sit between them and be missing from the Quaternary map. | Fleet radiometric fusions score the contact, not the offset. | Soil moisture, vegetation, flight-line striping. | **Not viable this session.** USGS GeoDAWN is the free CC0 source (<https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>). The large grids were not fetched or aligned here. Band 6's tag says tilt/curvature, but this session measured it strictly positive on 5,164,300 footprint pixels (min 2.95). It is not used as a signed tilt, and it is not treated as radiometric total count without a recomputed correlation. |
| 4 | Flight-direction spectral nuisance control | Band 2, plus official GeoDAWN flight-line azimuth. | Does not find new faults; it would remove levelling-seam false positives. | No directional spectral nuisance estimator is in `src/`. | A real fault parallel to the flight lines would be suppressed. | Low expected gain. Flight paths not fetched. Not run. |
| 5 | Within-unit mag–gravity offset | Bands 2 and 13, conditioned on USGS SGMC unit polygons. | An offset inside one mapped unit is less likely to be the unit contact the catalogue already implies. | CED is global, not within-unit. | Intrusive contacts and map-boundary generalisation. | **Not viable until retrieved.** Official lead: <https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a>. Not present locally; not fetched. |

## Preregistered experiments (max 3)

1. **E1 crest.** Unshifted cross-gradient parallelism, 37,654 unit dots, spacing 2.8 px, exact catalogue pixels excluded. Paired magnetic-gradient-only control, same budget.
2. **E2 shadow.** Same parallelism sampled `clip(H·cot(55°)/100, 2, 8)` px up-dip, soft cover weight, 32,000 dots, spacing 3.0 px.
3. **E3 deep shadow.** Only if E1 and E2 have not already duplicate-stopped the lane: shadow restricted to basement depth above the footprint 75th percentile, 12,000 dots, spacing 3.5 px.

Stop rule: if a surface rank-correlation with any checked registry raster exceeds 0.90, or more than 70% of emitted dots fall within 3 px of one registry raster's dots, log duplicate and do not place or continue that arm. No anti-registry noise. No weekly slot is selected here.
