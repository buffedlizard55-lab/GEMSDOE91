# MECHANISM CARDS — CONCENTRATION, second generation (session 8, 2026-10-24)

Three arms on R0 (`h33-h33-2-b2`, 37,654 unit dots, CLAIM `0.2778`). Every arm changes only
*which 1 km blocks hold the dots*: count fixed, unit mass, `>= 3 px` from the mapped catalogue,
`>= 2.0 px` from every other dot, R0's 2,171 collar dots quarantined in place. Fixed seed 91034.
Evidence: `evidence/concentration_struct_20261024.json`. Rasters: `releases/…-20261024-<sha8>.tif`.

## Shared design, and why these three and not more of the same

Seven CONCENTRATION rows already exist and all seven move mass **toward** whatever their prior
ranks highest. Both of the brief's own diagnostics say that direction is unpriced: every one of
them pushes the 1 km occupied-block CV *up* and away from the `0.51-0.59` band the best historical
files reportedly sit in, and the GDR-thermal family moves the label-blind catalogue PROXY *down*
(`-0.0008`) while a **uniform random** block ranking reproduces ~70 % of its predicted gain
(`evidence/concentration_axis_20261023.json → null_diagnostic`, `+0.0087` of `+0.0123`).

So the two questions this session built are about *dose* and about *what the parent has already
over-served*:

| arm | prior | dose | what it separates |
|---|---|---|---|
| `st1km-m10` | structural (bands 3/5/18 percentile mean) | 10 % | dose bracket **below** the fleet's existing 15 % / 1 km structural point |
| `st1km-m20` | same | 20 % | dose bracket **above** it |
| `res1km-m20` | structural rank **minus parent occupancy rank** | 20 % | is the parent's own clumping information or noise? |

**Prior definition (label-blind, pinned).** Percentile rank inside the footprint (ties averaged) of
Band 3 `tmi_hg`, Band 5 `iso_grav_anom_slope` and Band 18 `iso_grav_anom_hg` of
`data/bridge/gems-geodawn-numerical-features.tif` (sha256 `4371c82e…`), averaged; block mean at
1 km. Same three bands the ledger's existing `15pct-1km-grad` row names. The **residual** prior is
`rank_pct(structural block mean) − rank_pct(dots per block)` over *occupied* blocks only — empty
blocks are NaN and can never accept a dot. Measured correlation between structural rank and
occupancy rank: **`+0.0524`** — the parent's dots are essentially uncorrelated with the
geophysical structure at 1 km, which is exactly what makes the residual a different allocator
rather than the same one with a smaller number on it.

## Instruments (REPORT ONLY — never gates)

| instrument | R0 | reading |
|---|---|---|
| catalogue hide-and-recover PROXY (5 draws, ~12,200 withheld positives, 95 % CI ±0.00023) | `0.006186` | **identically unchanged (`+0.000000`) for all three arms** — every acceptor is `> 3 px` from the catalogue and every donor is quarantined, so the instrument is blind to this edit (the same invariance SNAP hit by construction, IR-91-28). It cannot rank these arms. |
| USGS SGMC bedrock faults, off-catalogue `> 3 px`, 62,122 cells ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | DTI `0.095386` | the only *independent* locator available here; **all three arms lose credit on it** — see each card. |
| leakage canary (moved-vs-withheld-catalogue AUC) | — | `0.4496` / `0.3991` / `0.3991`, all far below the `0.90` stop rule. The edit is not target-proximal. |
| null diagnostic (uniform-random block ranking, same 20 % dose, same seed, same collar rule) | — | surrogate `-0.0079`: random relocation **loses**. Unlike the GDR family, the structural prior's gain is not reproduced by relocating at random. |

The surrogate-truth DTI is the arm's own hypothesis used as truth (top 60,988 structural cells =
the mapped catalogue's cell count). It is a MODEL **ceiling**, not a prediction: by construction
the arm optimises the very field it is scored against. Predictions below follow the fleet's frozen
convention (`pred = 0.10 × 0.2778 × surrogate relative change`, floor from the uniform-noise and
H19-5 lineage-mask deltas, ceiling `3 ×` point).

---

## 1. `st1km-m10` — structural concentration at 10 %

`h33-h33-2-b2-CONCENTRATIONst1km-m10-20261024-45d1f4e9` · 37,654 dots · 3,765 moved (10.00 %) ·
mean displacement 1,652 px (16.5 km) · 1 km CV `0.6187 → 0.6468` · gates 16/16 + 14/14 PASS.

- **Hypothesis.** Fault location, not dot count, is the binding constraint: a fixed budget of dots
  placed where the geophysical structure says "fault" earns more kernel credit than the same
  budget placed by the parent's own density.
- **Mechanism.** TMI and isostatic-gravity horizontal gradients peak over the density/magnetisation
  contrast across a fault plane; the 1 km block mean suppresses single-pixel noise so the ranking
  reflects structure at the step-over scale (Faulds inventory) rather than a 100 m artefact.
  Percentile ranks make three bands with different units average without one dominating.
- **The non-fault process that could mimic it.** A lithological contact, a Tertiary unconformity or
  a flight-line/levelling edge produces the same gradient crest with no Quaternary displacement.
  A second mimic: the prior is **not independent of the lineage** — the H19-5 field was itself
  built from geophysical derivatives, so "concentrating on structure" may be re-encoding the same
  measurement the dots already encode rather than adding information.
- **Predicted live change.** **`+0.0062` MODEL, range `[-0.024, +0.019]`** (surrogate ceiling
  `+0.0616`; floor if truth is the H19-5 lineage mask `-0.0241`; SGMC `-0.0078` DTI ⇒ `-0.0228`
  if SGMC were live). **Sign genuinely uncertain.** `|Δ| < 0.01` live is not evidence.
- **Falsifier.** Live `≤ +0.0062` (the point estimate) while the 20 % arm moves further in the same
  direction ⇒ dose does not transfer, the structural prior is at best a weak locator, and the
  family is retired rather than re-dosed. Live `< -0.010` ⇒ the prior is a re-encoding of the
  lineage and CONCENTRATION on geophysics should be dropped in favour of the external GDR prior.

## 2. `st1km-m20` — structural concentration at 20 %

`h33-h33-2-b2-CONCENTRATIONst1km-m20-20261024-ba313f84` · 37,654 dots · 7,531 moved (20.00 %) ·
mean displacement 1,636 px (16.4 km) · 1 km CV `0.6187 → 0.6794` · gates 16/16 + 14/14 PASS.

- **Hypothesis / mechanism.** Identical to arm 1; the only change is the dose, which is what makes
  the pair a dose-response rather than two opinions. It also brackets the fleet's existing
  `15pct-1km-grad` (`+0.008` MODEL) from above.
- **The non-fault process that could mimic it.** As arm 1, plus a scale artefact: at 20 % the edit
  moves one dot in five, so any mismatch between the geophysical grid and the fault inventory
  (longer-wavelength filtering, upward continuation through basin fill) dominates the change rather
  than the structure itself.
- **Predicted live change.** **`+0.0116` MODEL, range `[-0.049, +0.035]`** (surrogate ceiling
  `+0.1162`; H19-5 floor `-0.0487`; SGMC `-0.0133` DTI ⇒ `-0.0387` if SGMC were live). The SGMC
  penalty is **1.7× the 10 % arm's**: on the only independent locator, more dose is worse.
- **Falsifier.** If this arm does not beat `st1km-m10` live by `≥ +0.005`, the dose response is flat
  or negative and no further re-dosing of a shell-tested prior is worth a slot. If it beats it by
  `≥ +0.010` *and* the SGMC sign is an artefact of mapped-fault geometry, then concentration pays
  and Week 2 should pair it with PRUNE.

## 3. `res1km-m20` — residual concentration at 20 %

`h33-h33-2-b2-CONCENTRATIONres1km-m20-20261024-d9a0fcc4` · 37,654 dots · 7,531 moved (20.00 %) ·
mean displacement 1,599 px (16.0 km) · 1 km CV **`0.6187 → 0.5867`, inside the 0.51-0.59 band** ·
gates 16/16 + 14/14 PASS.

- **Hypothesis.** The parent's field is dense in blocks for reasons that have nothing to do with
  structure — the H19-5 mask's own geometry, the d2.8 thinning, and the collar removal. Where
  occupancy is high *and* structure is low, those dots are the cheapest to move; where structure is
  high *and* occupancy is low, they are the most valuable to add. So the right allocator is the
  **residual**, not the prior.
- **Mechanism.** Two measured facts make the residual non-trivial rather than decorative:
  structural rank and occupancy rank are almost uncorrelated (`+0.0524`), and 30 % of R0's dots
  (11,415) have a neighbour within 2.83 px. Under the per-cell reading of `T` (IR-91-33) a dot
  whose truth cell is already covered by a neighbour earns nothing, while its 0.2 still sits in the
  denominator — so dots in over-served blocks are the most likely to be pure cost.
- **The non-fault process that could mimic it.** Occupancy is *not* a random sample: the parent's
  thinning kept the strongest parts of the H19-5 field, so a sparse block may be sparse because
  the field is weak there, not because it was over-thinned. A gain would then be mis-attributed to
  "de-clumping" when it is really "the field was right and we diluted it". That is what the
  lineage-mask floor measures: `-0.0524`, the worst of the three arms — if new-fault truth
  resembles the H19-5 mask, this arm is the most expensive one to run.
- **Predicted live change.** **`+0.0114` MODEL, range `[-0.052, +0.034]`** (surrogate ceiling
  `+0.1136`; SGMC `-0.0055` DTI ⇒ `-0.0161`, i.e. **2.4× gentler than the matched-dose
  `st1km-m20`** on the independent locator; noise-truth floor `+0.0009`, the only arm that is
  neutral-to-positive when the prior is pure noise).
- **Falsifier.** Live `≤` `st1km-m20` ⇒ the residual adds nothing over the prior at matched dose,
  and "the parent over-serves" is refuted; the CV band then has no causal claim and should be
  dropped from the brief's diagnostics. Live `< -0.010` ⇒ moving dots out of the parent's dense
  blocks destroys genuine signal, which also argues against the delete-only PRUNE arms and must be
  reconciled with their `+0.008` prediction before either is spent on a slot.

---

## What this session does **not** claim

- No arm is a receipt, a score, or evidence of a gain. Every number above is MODEL or PROXY.
- The catalogue PROXY is identically invariant for all three arms, so it neither supports nor
  rejects them; the SGMC control is the only independent locator and it is negative for all three.
- The surrogate ceiling is circular by construction and is reported only so the reader can see how
  far the fleet's `×0.10` convention discounts it.
- `TOP_PUBLIC` is still blank and R0's `0.2778` is still an unreceipted CLAIM, so "better" is still
  defined only against R0.
