# Mechanism cards — written for a structural geologist

Every card answers the same five questions, because a scored result plus a mechanism is
an experiment, while a scored result alone is a lottery ticket. Predicted magnitudes are
**MODEL** unless a receipt is quoted.

---

## CONCENTRATION — built (`tools/run_concentration.py`), not run

**Change from parent.** Move 10–20% of R0's dots out of the lowest-prior 5 km blocks and
into the highest-prior ones. Dot count, mass per dot, footprint and the catalogue
exclusions are all unchanged. Block size is a CLI parameter and is reported with the CV
before/after.

**Hypothesis.** At a fixed dot budget, the live score rises when dots are redistributed
toward the kilometre-scale blocks where faults are a-priori more likely.

**Mechanism.** The metric pays through kernel credit from truth within 3 px (300 m).
Block-scale prior (a smoothed multi-layer model, a catalogue-density prior computed on
blocks the parent was *not* built from, or the Faulds step-over/intersection prior) is
much more stable than any single-pixel response. Moving mass to high-prior blocks raises
T; because the count is fixed, S is untouched and `(S − M)` can only fall, so the
denominator does not grow.

**Non-fault process that could mimic it.** Survey geometry. If the prior tracks
flight-line density (400 m spacing over GeoDAWN Area 2), "high prior" may mean
"well sampled" rather than "more fault"; the catalogue buffer removes the direct
version of this (mass on known traces), but a residual version survives on chunks far
from known traces. A second mimic is clustering: more dots per block creates
over-dense clusters whose extra mass is capped at 1 per truth pixel, producing no
gain even when the prior is informative.

**Predicted sign and size.** Positive, **+0.004 to +0.020** live versus R0 (MODEL).
A live change under 0.01 is not evidence (brief §5); with 10% moved the effect should
land near the bottom of that range, with 20% near the top if the mechanism is linear.

**Falsifier.** Live Δ ≤ 0 while the realised percent-moved and block CV move as designed
⇒ the block prior carries no transferable information at this scale. Retire the axis;
do not "fix" it by tuning the fraction in a later slot.

**Watch item (recorded because it cuts against the axis).** Historical best files are
reported at block-density CV 0.51–0.59; concentration *raises* CV because it empties
some blocks and fills others. The builder reports a `cv_warning` when the CV leaves
0.45–0.70, and the reason the first slot uses 10% rather than 20% is to keep the two
effects separable.

---

## MASS — designed, **not buildable here**

**Change from parent.** Drop the lowest-ranked 10% of R0's dots, then a second file that
adds the next-ranked 10% instead. **Requires R0's own ranking artifact**, which is absent
and cannot be rebuilt from the raster (marginal-gain ranking needs the labels R0 was
ranked against). Re-ranking with a proxy would change the ranking *and* the mass, i.e.
two changes — forbidden by the brief's one-change rule. See `IRREGULARITIES.md` I-4.

**Hypothesis.** The dot budget sits on the wrong side of the pay threshold: the marginal
dot either pays or it does not, and the file is either under- or over-mass.

**Mechanism.** An extra unit dot is worth `c − 0.2·DTI` in the score, where `c` is its
kernel credit and `0.2·DTI ≈ 0.056` at 0.28 (MODEL; assumption-sensitive, see I-5).
Dropping the 10% of dots with the smallest credit removes mass that costs denominator
without buying numerator. *Note:* mass that lands on already-covered truth is exactly
neutral in this algebra — dS and dM cancel — so pruning only helps where the dots are
away from truth, which is why PRUNE and MASS are the same experiment seen from two sides.

**Mimic.** Any dot that sits near truth by chance (a dense cluster on a non-fault
lineament). The effect will look like "thinning helped" when it is really "the sparse
tail was noise".

**Prediction.** +0.006 to +0.015 for the drop-10% file (MODEL). The add-10% file is
expected to be flat-to-negative if R0 is near the threshold — that asymmetry is the
test.

**Falsifier.** Both directions score the same (or both worse) ⇒ the mass axis is inside
noise at this scale; the file is threshold-free and mass should be held fixed forever.

---

## PRUNE — designed, **partial** (needs the ranking for the refill step)

**Change from parent.** Remove every dot within 1, 2 (that is R0), and 3 px of the
catalogue, then refill to hold the count. The refill needs a ranking; without it the file
changes count *and* placement at once, so only the ≤3 px-without-refill version is a
legitimate one-change test, and it is confounded with MASS by construction.

**Hypothesis.** Dots hugging known traces pay nothing (those pixels are masked
pixel-exactly) and are pure denominator cost.

**Mechanism.** The organisers mask known USGS/INGENIOUS pixels pixel-exactly, so any mass
on them yields zero credit while still counting in S. A dot 1–3 px away may or may not
sit on newly mapped geometry — that is the uncertainty being tested.

**Mimic.** New-fault truth genuinely adjacent to known traces (forum answer: new-fault
truth can lie within 300 m of known traces). If the annulus is real signal, pruning it
*removes* score, and the sign of the prediction flips. That is why PRUNE is placed after
a CONCENTRATION dose-response rather than first.

**Prediction.** +0.003 to +0.012 (MODEL), small because mass near truth is nearly free
in the algebra.

**Falsifier.** The ≤3 px file loses score while R0's ≤2 px version is the best file
⇒ the annulus carries signal, and the next axis should be EDGE-FLOOR (see
`SLOT_PLAN.md`), not a wider prune.
