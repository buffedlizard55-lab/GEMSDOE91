# SLOT_PLAN — one page

State on 2026-10-23: **0 of 3 planned variants exist.** Preflight blocks every axis
(`make preflight` → exit 2). The reason is not a modelling choice, it is a missing
input list (see `IRREGULARITIES.md` I-1). The plan below is what happens the hour
the data lands; it is ordered by *information per slot*, not by expected score.

## Slot order

**Slot 1 — CONCENTRATION f10-blk50** (`tools/run_concentration.py`, prepinned).
15%→10% of dots moved from the lowest-prior 5 km blocks into the highest-prior ones,
count fixed, exclusions unchanged. Predicted **+0.004 to +0.020** (MODEL).
*What the result changes:* if ≥ +0.01, the km-scale prior is transferable signal and
slots 2–3 should push concentration harder (and the block-scale prior becomes the
backbone of the Phase-2 trace work). If |Δ| < 0.01, retire block prior as a lever and
never spend another slot on it. If ≤ −0.01, the prior is anti-correlated: check
immediately whether it is a survey-coverage proxy (falsifier on the mechanism card).

**Slot 2 — CONCENTRATION f20-blk50** *only if slot 1 clears +0.01*; otherwise
**PRUNE ≤3 px with refill** (needs `R0_ranking`; predicted +0.003 to +0.012).
Two points on the fraction axis turn a one-off into a dose-response, which is the
only cheap way to tell a real effect from chunk noise. If slot 1 was flat, PRUNE tests
a different, weaker mechanism (mass that M already credits is nearly free → small
effect expected under the algebra).

**Slot 3 — SNAP ≤2 px** (needs TMI + gravity gradients; predicted −0.000 to +0.010,
*sign genuinely uncertain*). Same count, mean displacement reported. This is the
cleanest test of "the dots are in the right place but 1–2 px off", which is the
400 m line-spacing hypothesis. Negative result here kills the positional story and
makes MASS the remaining lever — worth knowing before week 3.

## Then (weeks to 2026-12-03)

- wk 3–4: combine the two axes with the better receipts (one change per file, still),
  keep the better single-axis file as fallback.
- wk 5–6: confirm the leading file on a repeat-seed twin (proves the seed is not
  driving the result), choose the final file + a fallback, re-validate the format of
  both, and stop touching the pipeline.
- Reserve the final submission for the file with the best *receipt*, never the best
  MODEL number.

## Why not MASS / RELIEF / SPACING first

- **MASS** and **PRUNE-with-refill** are *not one-change* edits in this checkout:
  both need R0's own ranking (by exact marginal gain against the labels R0 was built
  on). Re-ranking with a proxy would change two things at once and teach nothing.
- **RELIEF** is cheap but the mechanism is weak (relief terciles are a coarse
  proxy for fault style, and the target is fault pixels, not geology).
- **SPACING** is the lowest-value axis: mass is confounded with field, and the ledger
  shows dot count is not the binding constraint.
- **TRACKB** is a Phase-2 deliverable, not a weekly slot.

## Proposed better axes (NOT built this session — for a future session)

1. **EDGE-FLOOR** — mechanism: the binding constraint may be non-fault truth *near*
   known traces (brief: new-fault truth can lie within 300 m of known geometry), so
   the highest-value dots are the ones just outside the catalogue buffer, not the
   most confident ones. Confounder: catalogue proximity is also survey quality.
   Falsifier: a file with mass concentrated in the 3–6 px annulus scores lower than
   one with the same mass placed by marginal gain away from the catalogue.
2. **DENSITY-CAP** — mechanism: the 0.51–0.59 block-density CV band suggests the
   metric rewards *even* coverage rather than peak density (T saturates at 1 per
   truth pixel, so over-dense dots buy nothing). Confounder: CV correlates with how
   many blocks the prior marks high. Falsifier: two files at matched count, CV 0.55
   vs 1.2, placed by the same prior — if the tighter one wins, spacing is causal.
3. **AMBIGUITY-BUDGET** — mechanism: allocate dots in proportion to positional
   uncertainty (400 m line spacing ⇒ ~2–3 px), i.e. exactly one dot per plausible
   trace position rather than one per confident pixel. Confounder: it is a
   re-parameterisation of SPACING. Falsifier: identical count, jitter-only change
   (±1 px of every dot), which isolates positional uncertainty from placement.
