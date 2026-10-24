# MTD91 — magnetic texture destruction / coherence-length (preregistered)

Written **before** holdout numbers were treated as a promotion decision.
Lane of session 2026-10-24, branch `arena/9f196bb4-gemsdoe91`. Budget: 3 experiments.

## Why fleet 0.2778 (CLAIM, GEMSDOE32 zeros twin)

Sparsified h19-5 ranking + catalogue collar. Beating it needs a **new detector**,
not a new emission of the same ridge field. Official DTI: DrivenData #306
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
(α=0.2, β=0.8, 300 m triangular kernel). GeoDAWN bands:
<https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
EPSG:32611 <https://epsg.io/32611>. Tversky/DTI background:
<https://en.wikipedia.org/wiki/Tversky_index>.

## Ranked untried hypotheses (this repo, 2026-10-24)

| Rank | Hypothesis | Layers | Missing-fault rationale | vs this repo | Δ / cost |
|---|---|---|---|---|---|
| 1 | **MTD91 (this lane)** structure-tensor isotropy + HF energy fraction | RTP band 2, \|TMI-VG\| band 9 | Damage-zone fracturing shortens magnetic fabric without a scarp | No structure-tensor / autocorrelation-length lane; H91 e3 is a *trough*, not ST+HF | Medium / low |
| 2 | Phase congruency / monogenic energy | rtp, iso_grav, det_elev | Contrast-invariant phase of buried steps | Not implemented | Med-high / high RAM |
| 3 | Drainage χ discontinuities | band 12 | Young traces offset piedmont drainages | Not implemented; 100 m DEM coarse | Low / med |
| 4 | 1 m 3DEP scarp as *features* | USGS 3DEP | Expert hidden faults are 1 m scarps | Blocked: sandbox cannot fetch USGS | Highest / **blocked** |
| 5 | ASC91 already ran (negative 0.1168 HOLDOUT-DTI) | — | — | Done | — |

Non-fault mimic for MTD91: **young volcanic flows** and **GeoDAWN flight-line levelling residuals**.

## Frozen method

See `src/gems91/mtd.py`. Catalogue only as >3 px collar. Shared holdout
`scripts/evaluate_holdout.py`, writer `scripts/submission_writer.py`.

E1 dest_RTP; E2 √(dest_RTP·dest_VG); E3 E2×isotropy mix.
