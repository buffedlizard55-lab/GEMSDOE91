# Mechanism cards — SNAP axis on R0 (built 2026-10-23)

For a structural geologist. One card per build. All three arms share one driver, one
radius and one exclusion rule; they differ only in how many dots are allowed to move.

Parent **R0** = `h33-h33-2-b2` (GEMSDOE32): 37,654 unit-mass dots, sha256
`baeae321…` (NaN) / `c55bafc4…` (zeros), rebuilt byte-exact this session from the two
pinned ancestors. R0's `0.2778` is a **CLAIM**, not a receipt. Nothing below is a score.

## Shared setup, measured not assumed

**Driver — the edge response being snapped to.** Bands 3 `tmi_hg` (total magnetic
intensity horizontal gradient) and 18 `iso_grav_anom_hg` (isostatic gravity anomaly
horizontal gradient) of the pinned GeoDAWN stack. Each is |·|- and `log1p`-compressed,
nearest-filled (3,061 sentinel cells inside the footprint), high-passed against a
600 m Gaussian and robustly scaled; the two are smoothed at 1.5 px and averaged.
The high-pass matters: a raw gradient has km-scale trends, and a 2 px window-max snap
on that field simply slides every dot uphill (a CONCENTRATION edit in disguise).

**Exclusions.** Targets must be inside the footprint and `d_cat > 3 px`. R0's 2,171
inherited dots at `2 < d_cat ≤ 3 px` are **quarantined in place** (IR-91-27), so
`collar_before = collar_after = 2,171` and zero new mass lands inside 3 px.

**Why the catalogue PROXY is identically zero — by construction.** Hide-and-recover
credit at a withheld catalogue cell is earned only by dots within the 3 px kernel.
SNAP targets are floored at `d_cat > 3 px`, and the only dots already inside 3 px are
the quarantined collar. No SNAP move can therefore change catalogue credit:
all three arms return `0.006186 → 0.006186` (5 draws, ~12,200 withheld positives per
draw, 95% CI `[0.005958, 0.006413]`). That is a design consequence, not evidence
(IR-91-28). The informative control is the **independent off-catalogue fault map**
(USGS SGMC, [DS-1052](https://pubs.usgs.gov/ds/1052/), 62,122 cells >3 px from the
catalogue), where credit *can* change.

**Measured dose and control response.**

| arm | rule | dots moved | % of 37,654 | mean disp. (all / moved) | SGMC ΔT/T | SGMC ΔDTI | 1 km block CV |
|---|---|---:|---:|---:|---:|---:|---:|
| R0 | — | — | — | — | — | 0.095386 | 0.6187 |
| `s2c` | 3×3 crest only | 2,047 | 5.44 % | 0.080 / 1.467 px | +0.08 % | **+0.00008** | 0.6194 |
| `s2q75` | window max, gain ≥ p75 | 4,495 | 11.94 % | 0.237 / 1.984 px | −2.5 % | **−0.00234** | 0.6217 |
| `s2f` | window max, no threshold | 35,174 | 93.41 % | 1.733 / 1.855 px | −9.8 % | **−0.00926** | 0.6446 |

All `REPORT-ONLY`/`PROXY`; SGMC is a different (bedrock) fault population and is never a gate.
Leakage canary: max single-band AUC against the catalogue `0.5793` (`geod_2ndinv`) ≪ 0.90;
moved-dot canary `0.47 / 0.44 / 0.03`.

**The metric algebra sets the price.** `DTI = T / (0.2T + 0.2(S−M) + 0.8|G|)`, so at fixed
denominator a live change of `+0.01` from `0.2778` needs `ΔT/T ≈ +3.6 %`. The arms deliver
`+0.08 %`, `−2.5 %` and `−9.8 %` on SGMC. Transfer with a 0.5 shrink for the population
mismatch gives the MODEL predictions below. The direction is what matters: on every
independent locator available, **the gradient crest is a slightly worse locator than R0's
own dots, and more snapping is worse**.

**What non-fault process could mimic this.** A dipping contact or a magnetised/faulted
block puts the horizontal-gradient maximum *downdip* of the surface trace — the classic
upward-continuation offset. At 400 m GeoDAWN line spacing (Area 2, 150–200 m above
terrain) that offset is of the same order as the 2 px window, so a snap can move a correct
dot onto the source edge rather than the fault. Pixel-scale noise in the derivative bands
produces local maxima that are not edges at all.

---

### 1. `s2c` — crest snap, 2,047 dots moved (5.44 %)

- **Hypothesis.** R0's dots are sub-resolution off the *local* edge crest, and moving the
  worst-off ~6 % of them by ≤2 px onto a 3×3 maximum recovers triangular-kernel credit
  without disturbing the rest of the field.
- **Mechanism.** Triangular kernel `R = 3 px`: a dot 1 px closer to truth gains `1/3` of
  full credit. The move is restricted to dots that already sit on a monotone flank of a
  local crest, so it is a position refinement, not a re-layout.
- **Mimic.** Noise maxima; the downdip gradient offset above.
- **Predicted live change.** `+0.000` `MODEL`, range `[−0.006, +0.006]` — i.e. expected to
  be **below the brief's 0.01 evidence bar**.
- **Falsifier.** Live `Δ ≥ +0.006`: local crests carry locational information and the dose
  should be raised in Week 2. Live `Δ ≤ −0.006`: gradient crests are systematically
  off-trace at this scale and SNAP is retired.

### 2. `s2q75` — window max for the largest-gain quarter, 4,495 dots moved (11.94 %)

- **Hypothesis.** If a crest snap helps at all, the dots with the largest driver gain are
  where it helps most; concentrating the move there should beat `s2c` if the mechanism is
  real and trail it if the driver is noise.
- **Mechanism.** Same kernel-credit argument, larger dose; the threshold is the 75th
  percentile of the per-dot window gain, fixed before the build.
- **Mimic.** Regional slope: high-gain dots are exactly those on steep flanks, so this arm
  is the one most exposed to drift masquerading as snapping.
- **Predicted live change.** `−0.004` `MODEL`, range `[−0.012, +0.005]`.
- **Falsifier.** `s2q75` beating `s2c` by `≥ +0.006` live means the dose-response is
  positive and the negative SGMC signal is a mapped-fault artefact; the reverse confirms
  the control.

### 3. `s2f` — full window-max snap, 35,174 dots moved (93.41 %)

- **Hypothesis.** The strong form: the TMI/gravity horizontal-gradient crest is a better
  locator than the lineage field everywhere, so every dot should move onto it.
- **Mechanism.** Every eligible dot goes to the strongest cell within 2 px. This is no
  longer a refinement: 93.4 % of dots move (dot-set Hamming 186.8 %), so the file is a
  re-derivation of the field from two gradient bands. A gain or loss must be attributed to
  *the gradient field as a locator*, not to "snapping" (IR-91-29).
- **Mimic.** Everything in the shared section, at full strength.
- **Predicted live change.** `−0.014` `MODEL`, range `[−0.028, +0.004]`. Pre-registered as
  the extreme arm: the SGMC control says it is the worst of the three, and previous
  single-signal lanes scored 0.00–0.19 live.
- **Falsifier.** Live `≥ 0.000` refutes the SGMC transfer for new faults — the gradient may
  locate unmapped faults that compilations miss. Live `≈ −0.014` confirms the transfer and
  retires SNAP for the rest of Phase 1.

---

**Slot guidance.** None of the three is predicted to beat R0; `s2c` is the only one whose
prediction is compatible with "no change". Use a SNAP slot only as an axis-retirement test,
and prefer `s2c`; `s2f` is the informative negative control, not a slot candidate.
