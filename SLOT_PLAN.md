# SLOT PLAN — one entity, 3 scored slots/week, deadline 2026-12-03 (unconfirmed)

**Status: no receipt exists anywhere in this lineage.** R0's 0.2778 is a CLAIM.
`TOP_PUBLIC` and "slots left" are still blank — the human must fill both.

## What session 5 changed about this plan

Session 5 built the MASS axis (three arms, `ledger/submissions.csv`) and, in doing so,
built the first **calibrated** local instrument this fleet has had. It changes two
things:

1. **Mass removal outside the masked collar is not free.** Every earlier prediction in
   this lineage assumed a dot far from the catalogue earns ~nothing, so deleting it
   only saves `0.2` of denominator. Measured on an independent unmasked fault map, a
   deleted dot earns **0.14–0.19 credit**, i.e. 3× the `0.2·DTI ≈ 0.056` break-even.
2. **Therefore the pending PRUNE ladder (session 4) is mis-ordered.** Measured with the
   same instrument at its own doses:

| ledger file | dots | change vs R0 | instrument ΔT | MODEL prediction |
|---|---:|---:|---:|---|
| `PRUNE le3-norefill` (1209e863) | 35,483 | 5.77 % | −139.1 | **−0.001** [−0.008, +0.007] |
| `PRUNE le8-norefill` (e1dd69d0) | 28,490 | 24.34 % | −1,306.2 | **−0.038** [−0.075, +0.004] |
| `PRUNE le15-norefill` (1ca1ff6f) | 21,989 | 41.60 % | −2,286.0 | **−0.068** [−0.129, +0.003] |

Rung 1 is a coin flip; rungs 2 and 3 are predicted losses of 4–7 points. Session 4's
`+0.006 / +0.010` came from assuming the 3–15 px shell is credit-free; the measurement
says it is not.

## The next three slots, in order

| # | file | what it is | predicted | what the result changes |
|---|---|---|---|---|
| 1 | **R0 itself** (`h33-h33-2-b2`, `c55bafc4…`) | the incumbent, resubmitted once | 0.2778 CLAIM → **a RECEIPT** | Nothing is measurable until this exists. Every prediction in five ledgers is unanchored to a real number, and the `le3`/`MASSsup10plus` results are only interpretable as *differences* from R0. **This is the highest-value slot in the whole plan and costs no building.** |
| 2 | `MASSsup10plus` (`…e23e5141`, 39,023 dots) | +3,540 highest-rank cells, ≥ 3 px collar | −0.002 [−0.007, +0.003] | The only arm whose *sign* the instrument does not settle: new credit 0.041/dot sits just under the 0.056 bar. A gain says the live metric tolerates unmatched mass far better than the algebra implies → reopen additions everywhere. A loss retires the "more mass" direction. |
| 3 | **the pure collar delete** = `R0 & (d_cat > 3)` | 35,483 dots, 5.77 % | −0.001 [−0.008, +0.007] | One number that settles the largest open question in the fleet: does deleting credit-free mass pay? It is the *measured* version of the parent's own best-ever step (+0.0070 CLAIM). **Caveat:** session 4's file (`…1209e863`) is not reproducible here — the same recipe gives 35,483 dots but sha `f848cf2d…`, so a rebuild must be entered as a NEW row (value `le3-rebuilt`), not as session 4's file (IR-91-18). |

Do **not** spend slot 2 or 3 on `le8` / `le15` / `sup24minus`: all three are predicted
losses of 3–7 points and the fleet has already spent 8 slots on exact repeats.

**Slots 1–3 are one week's quota.** If R0's receipt lands above TOP_PUBLIC, stop
climbing and start defending.

## Weeks to the deadline (2026-12-03, ~6 weeks)

| week | plan |
|---|---|
| now | Slots as above. Copy every receipt number into `receipt_score` + `receipt_date`. |
| wk 2 | Read the receipts against this table. If `le3` gains ≥ +0.01 → the withheld truth really is much sparser than any unmasked map, and the next three slots go to the upper PRUNE doses. If it is flat → mass is not the lever; stop pruning. |
| wk 3–4 | Whatever happens, the next axis needs an **independent fault-density prior resampled to 1 km blocks** (see below). Ask the human for `training_features.tif` again *and* for a licence check on any new external layer. |
| wk 5–6 | Choose the final file **blind** from the ledger, build a zeros fallback, re-validate both formats, re-read both from disk, and do not touch the winner afterwards. |

## Better axes (proposed, NOT built this session)

1. **PRIOR-MASS: rank dots by exact marginal gain against an independent fault map.**
   On the restrained SGMC instrument 87.9 % of R0's dots carry **zero** credit and the
   mean is 0.065, so a gain-ranked drop of the bottom decile is close to free
   (`+0.010` projected at 10 %, `+0.021` at 20 %). This is the one measured direction
   with a positive expectation. It is *not* built here because it would consume the
   only blind control this repo has. Mechanism: credit is a max over dots, so a dot
   that adds nothing to the max is pure denominator. Confounder: SGMC is a compilation
   of *mapped* faults, so the ranking would push mass away from known traces — exactly
   what the live mask already does. Falsifier: build **both** arms (gain-ranked and
   its sign flip) and require the pair to separate by ≥ 0.01.
2. **MASS-SHAPE at fixed count through the collar.** Every file in this lineage now
   sits ≥ 3.16 px from the catalogue, and the organizers say new faults can sit within
   300 m of known traces. Nobody has tested mass *at* 3–4 px without touching the
   catalogue. Falsifier: if 3–4 px mass scores at or below background, the organizer's
   "new faults near known traces" statement does not survive the mask, and the collar
   should be widened, not narrowed.
3. **TRACKB (Phase 2 only).** Unchanged: strike-consistent traces ≥ 1 km as GeoJSON +
   raster with one evidence paragraph each. Not a Phase-1 slot candidate.

## Two housekeeping rules this session adds

* A **`-zeros` twin is not gate-clean under `scripts/validate_release.py`**: it fails
  `nan_outside_footprint` by design. It passes 13/13 under
  `gems91.release_gates` with `zeros_outside_footprint` substituted. Upload the NaN
  primary; keep the zeros twin as the rules-allowed fallback.
* **Never mark a candidate BUILT without `collar_ge_3px`.** Six draft rows from this
  session are `SUPERSEDED-DRAFT` for exactly that reason (IR-91-03).
