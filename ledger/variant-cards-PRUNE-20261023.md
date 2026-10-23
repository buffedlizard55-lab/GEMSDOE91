# Variant cards — PRUNE ladder extension on R0 (built 2026-10-23)

Parent **R0** = `h33-h33-2-b2` (GEMSDOE32), 37,654 unit-mass dots, sha256
`c55bafc4…` (zeros) / `baeae321…` (NaN), dot-set digest `905cee9d…`.
R0's `0.2778` is a **CLAIM**, not a receipt. Nothing below is a score.

All three variants are **delete-only** PRUNE: remove every dot with
Euclidean distance `d_cat ≤ max_px` to the catalogue (60,988 px,
`data/derived/catalogue_mask.tif`), no refill. Count is not held, so each
file changes mass *and* geometry together — a gain cannot be attributed to
"avoiding the catalogue" alone, unlike a refill-held PRUNE. The choice is
deliberate: a refill needs the parent's ranking (absent; `training_features.tif`
has no public mirror), and guessing one would violate the brief's one-change rule.

Measured dose vs parent (from `evidence/prune_ladder_20261023.json`):

| variant | max_px | dots removed | % of R0 | n_dots | min d_cat remaining | proxy (catalogue) | SGMC within 3 px | block CV (1 km) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| R0 | — | — | — | 37,654 | 2.236 px | — | 15.5% | 0.619 |
| `le4-norefill` | 4.0 | 3,825 | 10.16% | 33,829 | 4.12 px | 0.0* | 13.3% | 0.626 |
| `le5-norefill` | 5.0 | 5,637 | 14.97% | 32,017 | 5.10 px | 0.0* | 12.8% | 0.626 |
| `le10-norefill` | 10.0 | 11,360 | 30.17% | 26,294 | 10.05 px | 0.0* | 12.5% | 0.627 |

\* Proxy is zero for all three because the proxy measures credit on *withheld
catalogue cells* (kernel R=3 px). Once every dot within 3 px is removed, no
remaining dot can touch a withheld catalogue cell, so the instrument is blind —
reported, not believed. Uniform-truth expected credit falls
0.068 → 0.061 (le4) → 0.058 (le5) → 0.047 (le10); the monotonic drop is the
mass loss, not arrangement.

---

### 1. `PRUNE-le4-norefill` — 3825 dots removed (10.16%), d_cat > 4 px

- **Hypothesis.** The 3–4 px shell (1,654 dots beyond the prior `le3` dose) is
  background carried by the parent's ranking and contributes denominator cost
  without new-fault credit. If true, extending the collar from 3 px to 4 px
  should be at least as beneficial as the 2–3 px step.
- **Mechanism.** Same as the prior ladder: a zero-credit dot costs `0.2` in the
  denominator (`α(S−M)`) for no numerator gain. Removing it raises DTI by
  `DTI·0.2/(den−0.2)` per dot (MODEL, den ∈ [48,800, 135,528] → +0.0004 to
  +0.0011 per 1k dots). The 3–4 px shell has zero catalogue credit by construction
  (all R0 catalogue credit lies within 3 px; kernel R=3 px), so its only possible
  value is new-fault credit within 300–400 m of known traces.
- **Non-fault process that could mimic it.** Geological splays at 300–400 m
  off the main trace (step-over relay geometry common in this terrane) and
  GeoDAWN flight-line uncertainty (400 m spacing, 150–200 m height → positional
  blur ≈ kernel radius). Deleting those dots would look like "denominator saving"
  when it is actually destroying real signal, but the mimic is weaker at 3–4 px
  than at 2–3 px because the organiser's "new faults within 300 m" statement no
  longer applies beyond 300 m.
- **Predicted sign and size.** **+0.003 MODEL** [−0.003, +0.009]. Slightly above
  `le3` (+0.002) because the dose adds 1,654 zero-credit dots; the interval
  reflects uncertainty in new-fault credit density at 300–400 m.
- **Falsifier.** If `le4` scores *below* `le3` or below R0 by ≥0.01, the 3–4 px
  shell carries real new-fault credit and the 400 m halo is not background;
  the next axis should *add* mass at 3–4 px, not remove it. If `le4` ≈ R0
  (|Δ|<0.01), the 3–4 px shell is neutral and the ladder should jump to `le10`.

### 2. `PRUNE-le5-norefill` — 5637 dots removed (14.97%), d_cat > 5 px

- **Hypothesis.** The effect scales with dose: if denominator saving dominates,
  a larger cut (adding the 4–5 px shell, 1,812 more dots, all zero catalogue
  credit) should out-gain `le4`. This tests linearity and prices the 400–500 m
  band separately.
- **Mechanism.** Identical to (1); the 4–5 px band is 400–500 m from known traces,
  well outside the organiser's 300 m clause, so the "new fault within 300 m of
  known trace" confound is absent. A gain here is cleaner evidence for
  denominator saving than `le3`/`le4`.
- **Non-fault mimic.** Long parallel strands or newly mapped extensions of existing
  systems that run 400–500 m off the mapped trace. The forum answer allows newly
  mapped geometry of existing systems to count as "new faults," so such strands
  would be truth and would be deleted here.
- **Predicted sign and size.** **+0.005 MODEL** [−0.004, +0.013]. The largest
  dose that keeps mass loss under 15% (the brief's RELIEF dose band) and leaves
  32k dots (85% of parent) — comparable to the MASS `m15drop` that was never
  receipt-tested.
- **Falsifier.** If `le5` underperforms `le4`, the 4–5 px band is the first band
  where new-fault credit outweighs denominator saving; the optimum lies between
  4 and 5 px and the next experiment should be a *refill-held* PRUNE at 5 px
  (once a ranking is available) to separate mass from placement.

### 3. `PRUNE-le10-norefill` — 11360 dots removed (30.17%), d_cat > 10 px

- **Hypothesis.** Most of R0's mass is far from known faults (median d_cat = 19.6 px;
  30% of dots sit within 10 px). If the new-fault field is sparse away from
  known systems, a large cut should win by sheer denominator reduction. This is
  the only variant in the ladder with a plausible path past the brief's ±0.01
  evidence threshold.
- **Mechanism.** Removes the entire 3–10 px halo (9,189 dots beyond `le3`, all zero
  catalogue credit) plus the 2–3 px collar. Denominator saving is ~2,272
  (`0.2·11360`) against a plausible new-fault credit loss that scales with the
  halo's area but with low fault density far from known traces.
- **Non-fault mimic.** Basin-scale fabric, lithologic contacts, or unmapped fault
  systems at km distances from known faults — the target is fault pixels, never
  basin centres, and the truth set may include isolated faults far from the
  catalogue. This dose maximally risks deleting them, which is why its interval
  is widest.
- **Predicted sign and size.** **+0.008 MODEL** [−0.006, +0.019]. Upper end
  reaches the evidence threshold; lower end allows a substantial loss if the
  halo is genuinely informative. The monotonic ladder `le3 (+0.002) < le4 (+0.003)
  < le5 (+0.005) < le8 (+0.006) < le10 (+0.008) < le15 (+0.010)` is the
  prediction to test — any non-monotonicity falsifies simple denominator saving.
- **Falsifier.** If `le10` scores flat vs R0 (|Δ|<0.01) while `le4`/`le5` also do,
  PRUNE is exhausted as an axis at all doses up to 30%: denominator saving is
  cancelled by credit loss everywhere, and the next slot should go to
  CONCENTRATION or RELIEF (block-scale prior transfer, not collar avoidance).
  If `le10` *loses* while `le4` gains, the optimum is inside the 4–10 px band
  and the next step is a bisection (e.g. 7 px) with a refill-held design.

---

## How the three are meant to be read together

| if the live result is … | the conclusion |
|---|---|
| Monotonic gain `le4 < le5 < le10` and `le10 ≥ R0+0.01` | Denominator saving dominates; the field is over-massed away from known faults. Next: bisection beyond 10 px (le12) or a refill-held PRUNE at the winning threshold once `training_features` is available. |
| `le4` gains but `le10` is flat or loses | Optimum inside 4–10 px; credit loss overtakes saving beyond it. Next: `le7`/`le8` to locate the peak, then refill-held at that dose. |
| All three within 0.01 of R0 and of each other | PRUNE is exhausted — no collar width between 4 and 10 px helps; denominator and credit cancel. Retire PRUNE, spend remaining slots on RELIEF or a CONCENTRATION re-cut with an external prior. |
| Any dose loses by ≥0.01 vs R0 | The halo carries real new-fault credit; R0's 2 px margin was already too aggressive. Next: add mass at 3–5 px (MASS `add` with ranking) or RELIEF from basin to range-front, not further pruning. |

**Common caveats.** (1) These are delete-only, so mass and placement are
confounded — a gain could be "fewer dots is better" (MASS) rather than
"away from catalogue is better" (PRUNE). The prior ladder noted the same
confound; only a refill-held variant separates them. (2) Hide-and-recover proxy
is degenerate here (0.0 for all doses beyond 3 px) and is not evidence.
(3) SGMC overlap drops 15.5% → 13.3% → 12.8% → 12.5% with dose, consistent with
mass removal, not with selective retention of SGMC structure.
