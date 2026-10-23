# Variant cards — SNAP axis (vertical-gradient ladder) on R0, Session 6

Full structural-geologist cards: [`docs/MECHANISM_CARDS.md`](../docs/MECHANISM_CARDS.md).
Numbers: [`evidence/snap_axis_20261023.json`](../evidence/snap_axis_20261023.json).

Parent **R0 = `h33-h33-2-b2`**, 37,654 unit-mass dots, sha256 `baeae321…c77dd` (NaN) /
`c55bafc4…6fa9` (zeros), `CLAIM` 0.2778. Rebuilt here from two pinned ancestors before
any edit (both reproduce the parent dot set exactly, `RECEIPT`).

**Treatment.** `driver = 0.50·pct(|Band 9 tmi_vg|) + 0.50·pct(|Band 11 iso_grav_anom_vg|)`;
each dot moves to the highest-driver cell within a **Euclidean** window of r px
(r = 1, 2, 3), ties to the shortest displacement; row-major order, no RNG.
**Held invariant in every arm:** count 37,654 · collar 2,171 → 2,171 (the inherited
2 < d_cat ≤ 3 px dots are frozen, not moved) · min nearest-neighbour ≥ 2.000 px
(R0: 0 pairs < 2 px) · no target at d_cat ≤ 3 px · zero catalogue mass.

| id | r | moved (`RECEIPT`) | mean disp (all / movers) `RECEIPT` | driver pct `PROXY` | SGMC Δ `PROXY` | frozen `MODEL` |
|---|---:|---|---:|---|---:|---|
| `h33-h33-2-b2-SNAPvg1px-20261023-97606a78` | 1 px | 33,807 (89.78%) | 0.898 / 1.000 px | 0.5360 → 0.5884 | −0.0033 | **+0.002** [−0.004, +0.008] |
| `h33-h33-2-b2-SNAPvg2px-20261023-353a9dda` | 2 px | 34,285 (91.05%) | 1.554 / 1.707 px | 0.5360 → 0.6142 | −0.0058 | **+0.003** [−0.005, +0.011] |
| `h33-h33-2-b2-SNAPvg3px-20261023-435435a3` | 3 px | 34,635 (91.98%) | 2.298 / 2.499 px | 0.5360 → 0.6367 | −0.0098 | **+0.004** [−0.008, +0.016] |

Zeros twins: `d22deb38…` / `c910a311…` / `81b14b91…`.

## 1. `SNAPvg1px` — the minimal nudge

- **Hypothesis.** Most of R0's positional error is sub-cell; 100 m toward the VG crest
  recovers kernel credit with almost no chance of jumping structure.
- **Mechanism.** 95.28 % of the movable dots shift, but only by 1.000 px (the 4-neighbour
  ring); the mean driver percentile at the dots rises 0.052.
- **Non-fault mimic.** Any smooth potential-field texture — basalt-flow edge, intrusive
  contact, playa density step, vertical-derivative survey artefact.
- **Predicted (frozen).** +0.002 `MODEL`; below the 0.01 bar by design.
- **Falsifier.** Live ≤ −0.004, or no separation from the random-shuffle null.

## 2. `SNAPvg2px` — the dose that matches the survey error

- **Hypothesis.** GeoDAWN Area 2 was flown at 400 m spacing, so the error process is
  ~200 m; this is the only arm both inside the brief's ≤ 2 px spec and matched to it.
- **Mechanism.** 96.62 % of movable dots move, mean 1.707 px for movers, max 2.000 px.
- **Non-fault mimic.** At 200 m a dot can cross from one structure's hanging-wall scarp to
  the next structure's footwall crest in a relay zone: a real fault, the wrong one.
- **Predicted (frozen).** +0.003 `MODEL`.
- **Falsifier.** Loses to the radius-2 random-shuffle null on an independent fault map.

## 3. `SNAPvg3px` — full kernel radius (outside the brief's ≤ 2 px spec, IR-91-29)

- **Hypothesis.** If the error is at kernel scale, the correction should be too.
- **Mechanism.** 97.61 % of movable dots move, mean 2.499 px for movers, max 3.000 px,
  driver percentile +0.101 — the strongest treatment in the ladder.
- **Non-fault mimic.** At 300 m the window spans a whole kernel: a dot can be dragged off a
  real trace onto a nearby canyon wall or fan toe and still *improve* the driver.
- **Predicted (frozen).** +0.004 `MODEL`.
- **Falsifier.** A monotone decrease with dose is decisive against the field itself.

## The control, and the honest bottom line

A report-only null (identical r = 2 machinery, uniformly random legal target, seed 91; no
raster, no ledger row, no slot) moves 32,157 dots, leaves the driver at 0.5363 (no
improvement) and costs **−0.0013** on SGMC.

| | R0 | null r=2 | vg1px | vg2px | vg3px |
|---|---:|---:|---:|---:|---:|
| SGMC off-cat DTI `PROXY` | 0.09539 | 0.09406 | 0.09210 | 0.08960 | 0.08560 |
| Δ vs R0 | — | −0.0013 | −0.0033 | −0.0058 | −0.0098 |
| × the null's loss | — | 1.0 | 2.5 | 4.4 | 7.4 |

The treatment removes **2.5–7.4× more** fault proximity than a coin-flip shuffle of the
same size, monotonically with dose, while its driver percentile rises monotonically. The
VG crest is therefore anti-correlated with mapped fault position at this scale: the more
faithfully the arm implements the mechanism, the worse it does.

**Post-hoc expectation (not pre-registered): the live sign is negative.** Size is not
measured — 1:1 transfer of the control Δ gives −0.003 … −0.010, relative transfer ~3× that,
no transfer 0. **None of these three is a slot candidate.** They are the falsification test for SNAP-on-VG; a live gain would
falsify the *control*, which is itself worth one slot if the human wants that question
answered (`vg2px` is the arm to spend it on: spec-compliant, largest contrast with the null).

The catalogue hide-and-recover `PROXY` is **identically 0.006186** for all four builds
including R0. That is blindness, not evidence of no effect — see IR-91-28.
