# Mechanism cards — CONCENTRATION on R0 (geodetic-strain prior), Session 8

For a structural geologist. One experiment, three arms; spend at most one slot on it
(and on this session's evidence, probably none — see the predictions). All numbers are
`RECEIPT` (re-read from disk), `PROXY` (local holdout/control) or `MODEL` (projection)
as labelled; no live score exists anywhere in this repository.

Build: `scripts/build_strain_concentration.py --build`; evidence
`evidence/strain_concentration_20261024.json`; design frozen before the build in
`registry/strain_concentration_preregistration.json`. Post-build control calibration:
`reports/strain_control_diagnostics_20261024.json` (`scripts/strain_diagnostics.py`).

## Shared setup, measured not assumed

Parent **R0** = `h33-h33-2-b2`, 37,654 unit-mass dots (`RECEIPT`, byte-rebuilt from both
pinned ancestors this session), claimed 0.2778 (`CLAIM`, no receipt). The moves are made
by the GDR fleet's own builder (`tools.run_concentration.build_concentration`) at the
same settings as slot-1 candidate `gdr25rm10` — 2.5 km (25 px) blocks, lowest/highest
30% of blocks, seed 91025, anchored acceptor placement (80% within ±4 px of an existing
high-block dot, 2 px minimum separation), count fixed — with exactly two differences:

1. **Prior source.** Sponsor GeoDAWN geodetic bands from the pinned
   `training_features` stack ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)):
   band 4 `geod_2ndinv`, band 7 `geod_shearrate`, band 8 `geod_dilaterate`.
   Each is Sentinel-filled (3,061 footprint px) and mapped to its average-tie
   percentile rank (`src/gems91/strain.py`, digests pinned in
   `registry/derived_priors.json`). Strain prior = mean of the band-4/7 ranks;
   dilatation prior = band-8 rank. At 2.5 km blocks the strain prior is
   near-orthogonal to the GDR thermal prior (Spearman 0.075, top-30% block overlap
   30.8% ≈ chance — measured before build, `RECEIPT`), so this is a new location
   hypothesis, not a re-dose of slot 1.
2. **Donor quarantine (IR-91-27/42).** R0's 2,171 inherited dots at 2 < d_cat ≤ 3 px
   stay in place; donors and acceptor targets all sit > 3 px from the catalogue
   (collar 2,171 → 2,171 in every arm, `RECEIPT`). The GDR build allowed collar
   donors and quietly removed 259–274 of them (2171 → 1897/1911/1912): its receipt,
   when bought, cannot be credited to the thermal prior alone (IR-91-42).

Three measurements define what this axis actually is:

- **The strain field is province-scale, not km-scale** (IR-91-44): autocorrelation 0.95
  at 25 km lag, 25 px vs 50 px block ranks 0.999, mean prior percentile 0.61 (west) vs
  0.34 (east) and 0.74 (south) vs 0.42 (north). Moving dots lowest→highest strain blocks
  is therefore a ~250 km NE→SW reallocation (mean displacement 2,493 px), however small
  the blocks are drawn. It tests *regional strain partitioning*, and cannot localise an
  individual fault to the 300 m kernel.
- **The two known-fault inventories disagree about strain.** Catalogue pixel rate rises
  across strain-prior deciles 0.88% → 1.89%, but SGMC-only fault pixels ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/),
  off-catalogue, > 3 px: 62,122 px — the closest local analogue of the target
  "not already captured by USGS/INGENIOUS") show no rise (1.32, 2.21, 1.26, 0.83, 0.65,
  0.89, 0.90, 1.12, 1.49, 1.34%). The bands' catalogue AUCs (0.579/0.576 `PROXY`, the
  numbers that put strain at the top of the proposal list) are therefore measuring
  where the *catalogue* is dense in high-strain country at least as much as where
  unmapped faults are.
- **The catalogue PROXY is identically unchanged** (`0.006186 → 0.006186`, 5 draws,
  ~12,200 withheld positives, CI [0.005958, 0.006413]) by construction — donors and
  targets are floored outside the 3 px kernel of every catalogue pixel (IR-91-28).
  It is reported for completeness and carries no evidence either way.

Predictions below use the preregistered translator (the SNAP session's own:
`0.2778 × relative SGMC kernel-credit change × 0.5`), applied identically to every
arm; the interval floor is the worse of uniform-noise truth (≈0 in all arms) and the
H19-5 lineage-mask truth bound. Calibrated on controls, the same translator reads the
concentration *operation under a random prior* at −0.0040 and the GDR priors at
−0.0009/−0.0024 (`PROXY`): GDR beats its null, strain does not.

## Card 1 — `strn25m10` (strain, 10% moved: 3,765 dots)

- **Hypothesis.** Blocks of high interseismic strain rate must be accommodating that
  strain on structures; where the mapped catalogue is thin, some of those structures
  are unmapped Quaternary splays and stepovers, so a fixed dot budget earns more kernel
  credit re-weighted toward high-strain blocks.
- **Mechanism.** Count fixed, so S is untouched; the edit can only win through T.
  Donor blocks average prior-percentile 0.09, acceptor blocks are in the top 30%.
  If new-fault density followed the catalogue's strain gradient (~2× bottom→top
  decile), a 10% move would be worth roughly +3–5% relative T, i.e. ≈ +0.010 live
  (`MODEL` algebra). That is the size the mechanism needs; it is not what the control
  measures (below).
- **Non-fault process that could mimic it.** Mapping/survey effort and strain
  partitioning onto *already mapped* through-going systems: high strain in the
  southwest quadrant may be fully taken up by known Walker Lane / Eastern California
  structures (masked), leaving no surplus for new faults, while the catalogue-density
  gradient that motivates the prior simply records where those systems were mapped.
  Geodetic smoothing is the second mimic: at 0.95 autocorrelation over 25 km the
  "prior" cannot distinguish a faulted block from its unfaulted neighbour.
- **Predicted sign and size.** **−0.0056 `MODEL` [−0.025, −0.003]** — negative.
  SGMC kernel credit falls 4.1% relative (T 5,517.6 → 5,294.0), worse than the
  random-prior operation cost (−2.9%). The H19-5 lineage bound is −0.025.
- **Falsifier.** A live Δ ≥ +0.010 for this arm would falsify the SGMC translator
  for block-prior edits generally (not just strain) and rehabilitate province-scale
  priors. A live Δ within ±0.010 is no evidence. This arm is the only strain file
  worth a retirement-test slot if the human wants one bought at all.

## Card 2 — `strn25m20` (strain, 20% moved: 7,531 dots)

- **Hypothesis.** The pre-proposal's own falsifier dose: if the strain mechanism is
  real and roughly linear, doubling the dose should roughly double card 1's gain until
  acceptor blocks saturate (anchored placement piles moved dots within a few px of
  dots already there, where their kernels duplicate existing coverage).
- **Mechanism / mimic.** As card 1, with saturation and donor-depth working against
  it: the second 10% of donors come from higher-prior blocks (donor mean percentile
  0.12 vs 0.09) and land in already-densified blocks (occupied-block CV at 2.5 km
  0.762 → 0.855, vs 0.807 at 10%).
- **Predicted sign and size.** **−0.0200 `MODEL` [−0.051, −0.010]** (SGMC T −14.4%
  relative). Locally the dose-response is monotone *against* the axis: on the only
  independent fault map available, more strain-concentration is worse, faster than
  linearly. **Not a slot candidate.**
- **Falsifier.** As card 1; a non-negative live receipt here would have to overcome
  both the SGMC sign and the saturation geometry, and would indict SGMC coverage in
  the southwest rather than vindicate strain per se.

## Card 3 — `strd25m10` (dilatation, 10% moved: 3,765 dots)

- **Hypothesis.** The extensional component, not shear-dominated strain magnitude, is
  what locates new Basin-and-Range normal-fault geometry: dilational jogs and
  stepovers are the classic upflow sites, and areal expansion is the strain those
  faults actually release. Band 8 is near-orthogonal to bands 4/7 (Spearman 0.05–0.28),
  so this arm discriminates tensor components rather than echoing card 1.
- **Mechanism / mimic.** High percentile = most positive dilatation (expansion) —
  the pinned band description's sign reading, recorded as an assumption. Mimic:
  broad basin subsidence/volcanic inflation signals and the same smoothing as cards
  1–2; also, pure-shear extension can be taken up distributively (many small faults
  below mapping scale) without producing mappable new traces.
- **Predicted sign and size.** **−0.0152 `MODEL` [−0.030, −0.008]** (SGMC T −11.0%).
  The independent map is harsher still: SGMC density in the top dilatation decile is
  the *lowest* of any decile (0.53%), so this arm moves mass into the decile where
  off-catalogue mapped faults are scarcest. **Not a slot candidate.**
- **Falsifier.** A live Δ ≥ +0.010 would say expert-expanded Phase-2 style labels
  reward extensional-basin traces that SGMC state maps miss — possible, but it is a
  conjecture to buy only after a cheaper axis has been receipted.

## What this session changes

- No strain arm is queued (preregistered rule: a strain arm could take a queue slot
  only at predicted ≥ +0.010; none is). The concurrent collar session (`arena/40027ebc`,
  merged first in PR #24) independently reached the same operational conclusion from
  the other side and revised the queue to R0 anchor → `PRUNE-le10` → `MASScons3add`;
  strain sits behind its `anti10` reserve: at most one slot, `strn25m10`, and only if a
  concentration-family receipt first discredits the SGMC translator for relocation
  edits in general. (This card's IR numbers were renumbered 33/34/35 → 42/43/44 at
  that merge; both concurrent sessions had numbered from IR-91-33.)
- Catalogue-AUC ranking of candidate priors is retired as a selection argument in
  this repo: for the strain bands it pointed exactly opposite to the off-catalogue
  map. Future priors should be screened on SGMC-off deciles as report-only evidence
  before a build, with the proxy-tuning risk stated (IR-91-44).
