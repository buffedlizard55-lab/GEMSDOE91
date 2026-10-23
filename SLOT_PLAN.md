# SLOT PLAN — 2026-10-23 (SPACING session)

**No automatic slot use.** One entity, ≤ 3 scored submissions per rolling week
([rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf)). The remaining quota and
`TOP_PUBLIC` are **unsupplied by the human** — I did not guess them. A live
change under ±0.01 is no evidence. R0 = `h33-h33-2-b2` (**0.2778 CLAIM**, no
receipt in any ledger).

Deadline arithmetic: 2026-10-23 → **2026-12-03** is 41 days ≈ 5.9 weeks ⇒ ≈ 17
slots, one of which is the blind final pick. The date is user-supplied and
**UNVERIFIED**.

## What this session's axis says

**SPACING was the only axis in brief §1 that no session had built** (grep of five
fleet ledgers: 132 + 129 + 22 + 20 + 5 rows, zero `axis=SPACING`). It is now
built three ways on one parent, with the count fixed and the displacement budget
identical (the radius-2 ring, 2.0–2.24 px):

| arm | what moves | relocated | mean disp. | density at target | predicted |
|---|---|---:|---:|---|---|
| `spread40` | 40 % of dots → emptiest legal ring cell | 15,056 (39.99 %) | 2.23 px | 0.066 → **0.035** | **+0.004 MODEL** [−0.004, +0.012] |
| `clump40` | same dots → densest legal ring cell | 14,973 (39.76 %) | 2.13 px | 0.066 → 0.058 | **−0.002 MODEL** [−0.010, +0.006] |
| `jitter40` | same dots → random legal ring cell (null) | 15,038 (39.94 %) | 2.15 px | 0.066 → 0.047 | **0.000** [−0.008, +0.008] |

**The axis is bounded, and the bound is the finding.** Under a uniform truth
prior the edit changes expected kernel credit by −0.17 % (spread) to −2.4 %
(clump); uncovered footprint cells fall by 1.3 % (spread), rise 0.5 % (clump).
At DTI ≈ 0.28 that caps the plausible live effect near **0.003**. A live change
of ≥0.01 on this axis would therefore be evidence of something *other* than the
spacing edit — which is exactly what makes one slot worth spending on it.

The catalogue hide-and-recover proxy moves the same way (+15 % / −8 % / −1 %),
but it cannot be used as support: only dots 2–3 px from the catalogue can touch
a withheld catalogue cell, and `spread40` pushes 815 dots into that collar
against 485 out. **The proxy is measuring collar drift, not spacing.** Leakage
canary 0.36–0.46 (no target proximity); all gates pass on all six files.

## Next three slots, in order

| # | file (upload the `-zeros` twin) | why this one | decision rule |
|---|---|---|---|
| 0 | *no slot* — supply facts | R0's receipt for 0.2778, `TOP_PUBLIC` + date, and slots remaining. Without them every MODEL in this ledger is unscaled and the 0.01 floor cannot be applied | — |
| 1 | `PRUNE-le3p000` (built by GEMSDOE86; re-validate before upload) | the only axis in the project with a **measured live dose-response**: 0.2708 → 0.2778 for 2,545 collar dots, +2.75 × 10⁻⁶ per dot — an order of magnitude above the metric's own zero-credit estimate. It is the best *bet*, and this session's build is not | ≥ +0.010 → the collar is not exhausted; next week a 4 px rung. Flat or ≤ −0.010 → PRUNE closes for Phase 1 |
| 2 | `releases/h33-…-SPACINGspread40-20261023-6d389309-zeros.tif` | closes the last unbuilt axis; the only arm whose mechanism predicts a *sign* and whose null control is built and matched | ≥ +0.010 → arrangement carries signal; next cut is spread at 50 % and a larger ring. Flat (abs change < 0.010) → **geometry is retired**; no further slots on SPACING, MASS or SNAP. ≤ −0.010 → the parent's clusters are real structure; protect them |
| 3 | `RELIEF-frontp15` (built by GEMSDOE86) **or** `CONCENTRATION conc15` if slot 2 was flat | the only built variants that move mass between places instead of deleting it; if slot 2 retires geometry, allocation is the remaining lever | RELIEF ≥ +0.010 → build RELIEF-ADD (count raised) and combine with PRUNE. Otherwise the final file is the better of PRUNE and RELIEF plus whichever arm separates from 0 |

**Why slot 1 is not this session's build.** `spread40` is predicted +0.004, the
same as `PRUNE-le3p000`, but its effect is *bounded* near 0.003 by the uniform-
truth ceiling and it has no live anchor behind it. Slot 1 goes to the axis whose
prediction rests on a measured rate; SPACING takes slot 2 because it is the only
axis that can still be *retired*, and retiring it frees every remaining slot.

**Do not spend a slot on:** `SPACINGclump40` and `SPACINGjitter40` (controls,
predicted ≤ 0), the other two PRUNE rungs, either MASS rung, or any SNAP arm —
prior sessions measured SNAP's proxy as *negative* and its dose is not
separable from a random-jitter null.

## Calendar to the deadline

- **wk 1.** Slot 1 `PRUNE-le3p000`. The collar's last rung, on the only
  measured rate the project has.
- **wk 2.** Slot 2 `SPACINGspread40`. One decisive read on whether arrangement
  matters at all — and if it does not, geometry stops consuming slots.
- **wk 3.** Slot 3 `RELIEF-frontp15` (or `conc15` if slot 2 retired geometry).
- **wk 4.** Re-cut the surviving axis at a second value, preregistered first.
- **wk 5.** Combine the two survivors into **one attributable edit**.
- **wk 6.** Confirm both finalists, re-validate both formats, choose the final
  file and a fallback blind. Never multiply accounts.

## Better axes (proposals only — not built this session)

- **Anisotropic packing (structure-tensor, σ = 3 px).** Pack dots 2 px
  along-strike and 4 px across-strike at matched area density, using the
  catalogue's local orientation. *Mechanism:* credit per dot is higher on a
  line-like truth. *Confounder:* the parent is already line-like, so the edit may
  be a no-op; new faults may sit at a high angle to mapped strands.
  *Falsifier:* no separation from `jitter40` in two independent draws.
- **Ring-4 spacing (4 px, 25 % of dots).** Tests whether the bound above is a
  dose artefact: if 2 px is capped at 0.003 but 4 px is not, the mechanism is
  real and merely under-dosed. *Falsifier:* live effect stays flat while the
  uniform-truth credit moves >1 %.
- **Receipt-first calibration.** No axis at all: re-submit the parent to convert
  0.2778 from CLAIM to RECEIPT, then re-anchor every MODEL in the ledger. This
  is the cheapest information per slot in the whole project and the only one
  that would let the 0.01 floor do any work.
