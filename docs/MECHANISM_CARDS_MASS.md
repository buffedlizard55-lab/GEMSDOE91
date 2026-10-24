# Mechanism cards — MASS axis, expansion arms (session 8, 2026-10-24)

Parent R0 = `h33-h33-2-b2` (GEMSDOE32), 37,654 unit-mass dots, sha256 `baeae321…c77dd`
(NaN) / `c55bafc4…6fa9` (zeros), CLAIM 0.2778. Rebuilt byte-exact from the pinned pair before
any arm was built (`scripts/build_mass_expand.py`, `verify_parent()`); 8 pinned inputs
sha256-verified first.

Cards are written for a structural geologist. Nothing here is a score: predictions are
**MODEL**, the independent fault map is a **PROXY**, and R0's 0.2778 is still a **CLAIM**.

---

## 0. What all three arms share (the one variable is the count)

**Ranking — the parent's own, recovered.** The ledger and the manifest record the parent's
MASS ranking as unrecoverable ("every pinned ancestor is binary"). That is true of a
continuous score and false of the ranking that decides this experiment: the lineage field
`anc_h19_5` (`calib_h195_01922.tif`, 121,131 px) **contains all 37,654 R0 dots**, and
**83,477 of its cells are not in R0**. R0 = that field after (a) a 2-px spacing thinning and
(b) "delete everything ≤2 px from the catalogue". Both steps removed cells by *geometry*,
not by score, so the unused cells are exactly "the next cells the parent's own model
selected". Within the field the lineage's only recorded ordering is cross-field support
(vote 0-3 over `anc_h19_5`/`h19_4`/`h16_1`), so every arm takes **vote-3 cells only**
(46,025 eligible cells >3 px off the catalogue). The tie-break inside a vote stratum is a
seeded shuffle (seed 91024), because a binary field has nothing left to sort on.

**Metric mechanism (why adding mass at all).** With
`DTI = T / (0.2T + 0.2(S − M) + 0.8|G|)`, a dot contributes credit `c` to `T` and costs
`0.2·(1 − m)` in the denominator, where `m` is its own best kernel value against truth. A
dot that lands inside the 3-px kernel has `m → 1`, so **mass that lands near truth is close
to free while every unit of its credit is added**. The first-order break-even probability
for *adding* a dot is `p* = 0.2·DTI/(c + 0.2·DTI·m) ≈ 0.018–0.036` for `c = 1.5–3` — i.e.
an added dot pays whenever it has better than ~2–4 % odds of truth within 3 px, against an
estimated ~12 % for the lineage's own accepted cells. Every fleet axis so far has been a
relocation or a delete at a 10–20 % dose; the count has been raised exactly once, by 10 %
(`MASScons3add`, +0.0086 MODEL), against `MASSm10plus` (−0.010) from the upstream import.

**What the edit is not.** No parent dot is moved, thinned or deleted; no cell within 3.16 px
of the catalogue is used (min added→catalogue distance 3.16 px), so the edit introduces
**zero** new collar violations — the 2,171 inherited dots at 2 < d ≤ 3 px are R0's own
(IR-91-03, unchanged and still the human's call).

---

## 1. `a12adj` — +4,707 dots (12.5 %) stacked 8-adjacent to accepted cells

- **Raster:** `releases/h33-h33-2-b2-MASSa12adj-20261024-d3de6292.tif` (42,361 dots)
- **Hypothesis.** Adding mass on cells that touch an already-accepted R0 dot raises the live
  DTI by more than the added denominator cost, because those cells inherit the parent's
  locational precision.
- **Mechanism (geological).** A dot field of 1-px lines has been sampled at 2-px spacing by
  the lineage's thinning. Fault traces are continuous at the 100-m grid scale: the cell
  beside an accepted trace pixel is usually the same trace, or its damage zone. The domain
  analogue is sampling a scarp twice across its width rather than once — the second sample
  buys kernel credit for free because it is inside the same 300 m kernel.
- **Non-fault process that could mimic it.** *Nothing but the metric's own degeneracy.* This
  arm can win without any geological truth: if the scorer's `0.2(S − M)` term is small
  compared to `0.8|G|`, matched mass is nearly free and any doubling of mass along correct
  traces pays. A gain therefore supports "mass is free where it is right" — it does **not**
  by itself prove the extra cells are new fault pixels. The `a12spc` twin is what separates
  those two readings.
- **Predicted sign and size.** **+0.009** MODEL (fleet per-dot calibration 1.85e-6/dot ×
  4,707), algebra sweep −0.004 … +0.042. Independent check (PROXY, report-only): the added
  cells are **more** often within 1 px of an off-catalogue USGS SGMC fault than R0's own
  dots (6.67 % vs 5.66 %; 2 px: 10.33 % vs 9.33 %) — the added cells are, if anything,
  better located than the parent's.
- **Falsifier.** A live Δ ≤ −0.005 with 12.5 % more mass and no dot removed says the
  denominator penalises unmatched mass much harder than the algebra allows (or the scorer
  caps density). Then MASS expansion is dead and no larger dose is worth a slot.

## 2. `a25adj` — +9,414 dots (25.0 %), same rule

- **Raster:** `releases/h33-h33-2-b2-MASSa25adj-20261024-c658eb33.tif` (47,068 dots)
- **Hypothesis.** Same mechanism at twice the dose; a genuine mass effect should be roughly
  linear in the number of added dots over this range, so `a25adj − R0 ≈ 2 × (a12adj − R0)`.
- **Mechanism.** As above; also the first count test in the lineage at a dose large enough to
  clear the brief's 0.01 evidence bar.
- **Mimic.** Compounding of the same metric degeneracy; at 25 % the added cells reach further
  out (mean 1.14 px, max 1.41 px from a parent dot — same as `a12adj` because the pool is
  the 8-neighbourhood), so the mimic risk is unchanged, not larger.
- **Predicted sign and size.** **+0.017** MODEL, sweep −0.009 … +0.085.
- **Falsifier.** If `a25adj` is flat while `a12adj` is positive, the mass response saturates
  below 25 % and the next session belongs on precision (CONCENTRATION/RELIEF), not count. If
  both are flat, MASS is the third axis retired by a receipt.

## 3. `a12spc` — +4,707 dots (12.5 %) at cells that touch no dot

- **Raster:** `releases/h33-h33-2-b2-MASSa12spc-20261024-d466d2ac.tif` (42,361 dots)
- **Hypothesis.** The spacing control. Same count, same field, same vote-3 stratum as
  `a12adj`, but every added cell is >1.41 px from any dot and no two dots are 8-adjacent — the
  parent's own texture ("37,654 dots, not one with an 8-neighbour") is preserved exactly.
- **Mechanism.** These are the *next* cells along the same field traces, one step further
  from accepted mass. If kernel credit, not proximity-to-accepted-dots, is what pays, this
  arm should match `a12adj`; if proximity is what pays, it should not.
- **Non-fault process that could mimic it.** None specific: this is the arm whose job is to
  *remove* a confound from the other two, not to win a slot. It also carries the SPACING
  confound the other arms have (they densify texture; this one does not).
- **Predicted sign and size.** **+0.005** MODEL, sweep −0.003 … +0.025. Independent check
  (PROXY): its added cells are **worse** than R0's dots on the off-catalogue SGMC map
  (5.44 % vs 5.66 % at 1 px), the opposite of `a12adj`.
- **Falsifier / reading.** `a12adj − a12spc ≥ +0.010` ⇒ clustering on accepted mass is the
  active ingredient and the mechanism is "matched mass is nearly free", pursued by dose.
  `a12adj ≈ a12spc` ⇒ the effect is count, not clustering, and the SPACING confound in the
  other two arms is immaterial.

---

## Report-only instruments (never gates, never scores)

| instrument | value | reading |
|---|---|---|
| leakage canary (vote 0-3 vs catalogue ring) | AUC **0.529** | ≪ 0.90, below the alarm threshold |
| SGMC off-catalogue enrichment, added vs parent (1 px) | `a12adj` 1.18×, `a25adj` 1.16×, `a12spc` 0.96× | independent map prefers the stacked cells |
| catalogue hide-and-recover PROXY | **invariant by construction** | every added cell is >3 px off the catalogue and nothing moves, so the proxy cannot move; it has no power over this axis |
| `release_gates.validate_release` (NaN + zeros twins) | **PASS, all gates** | shipped through this module, as every axis since session 3 |
| `gems91.gates.validate` (second implementation) | NOT CERTIFIED — `collar_ge_3px` only | inherited R0 collar, IR-91-03; the edit adds 0 dots inside 3 px |

## What a receipt on these three would settle

The fleet is 50 BUILD rows deep with 0 receipts, so every "best axis" claim in
`SLOT_PLAN.md` is a projection. This ladder is built to be informative in **one** week:
one dose contrast (`a12adj` vs `a25adj`) and one geometry contrast (`a12adj` vs `a12spc`),
all three from the same parent by the same rule. A single receipt at +0.01 or better on
`a25adj` would be the first positive evidence in the lineage that mass, not location, is the
binding constraint — and it would also fix the per-dot coefficient used for every future
prediction in this repo.
