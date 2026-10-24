# Mechanism cards — CONCENTRATION on the legal collar (session 8, 2026-10-24)

For a structural geologist. Parent `R0 = h33-h33-2-b2-20261004-e5eb6e7e`, 37,654 unit
dots, `0.2778` CLAIM. Built by `scripts/build_concentration_collar.py`; numbers in
`evidence/concentration_collar_axis_20261024.json`. Axis: **CONCENTRATION** — mass
moved, never added or removed (`S = 37,654` in every arm), so the only lever is where
the dots sit.

## The shared design

Dots are ranked first by the mean *collar prior* of their 1 km block (lowest first),
then by distance to the mapped catalogue (most remote first), then by raster index.
Acceptor cells are ranked by a linear ramp that is 1.0 at 3.05 px from the nearest
mapped-trace pixel and 0.0 at 6.0 px, multiplied by a 0.5–1.0 factor for how many of
the three pinned lineage fields emit the cell. Every acceptor clears the 3.05 px floor,
never lands on a catalogue pixel, and never creates a neighbour pair closer than R0's
own 2.828 px. `collar10` and `anti10` move the **same number of dots** with the
**same machinery** and **opposite priors**: their difference is the experiment.

Why this prior is worth a slot at all — measured, in `measured_prior_density`:

| distance to mapped trace | cells | fault credit/cell, SGMC off-catalogue | fault credit/cell, live-calibrated reference |
|---|---:|---:|---:|
| 3.0–4.5 px | 240,798 | 0.0533 | 0.0148 |
| 4.5–6 px | 157,746 | 0.0543 | 0.0124 |
| 6–10 px | 479,356 | 0.0455 | 0.0100 |
| >10 px | 3,883,149 | 0.0407 | 0.0069 |

R0 spends 49.4 % of its dots more than 10 px from any mapped trace (20.0 % beyond
50 px). The band just outside the 3 px exclusion is the densest legal place to put a
dot in both references — 1.3x (independent SGMC catalogue) to 2.1x (lineage field at
live density).

## `collar10` — `h33-h33-2-b2-CONCENTRATIONcollar10-20261024-00cfbe95`

`3,765` dots (10.00 %, Hamming 19.998 %) moved from the far field into the 3.05–6 px
band; mean displacement 1,593 px; band census 4,969 → 8,734; block-density CV
(1 km, occupied blocks) 0.6187 → 0.6037.

- **Hypothesis.** Some of the region's new-fault truth is unmapped splay/step-over
  geometry within a few hundred metres of mapped traces, so a dot at 300–600 m from a
  known trace has a better chance of earning kernel credit than a dot 5 km away.
- **Mechanism.** The organiser states known USGS/INGENIOUS pixels are masked
  pixel-exactly, that pixels *beside* them are scored normally against new-fault truth
  only, and that new-fault truth can lie within 300 m of known traces
  ([clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)).
  A 3 px kernel means credit exists only within 300 m: the 3.05–6 px band is the legal
  place from which a dot can still credit an unmapped trace that runs alongside a
  mapped one, and the measured cell densities above are that statement in numbers.
- **Non-fault mimic.** *Mapping-effort, not fault density.* The catalogue is denser
  where geologists worked, so "near a mapped trace" can mean "near a mapped area"
  rather than "near a fault". It would produce exactly the pattern measured here and
  would die in Phase 2, where experts expand labels after reviewing submitted faults.
- **Predicted live change (MODEL).** **−0.006**, range `[−0.026, +0.008]`. The point
  is the transfer of the independent SGMC off-catalogue control (−2.0 % relative),
  not a hope: on the only reference that is a *fault catalogue*, hugging the mapped
  traces costs a little. The upside in the range is the hypothesis: if new faults
  really do track the traces, the same edit is worth roughly +0.03 per dot on the
  measured collar advantage, i.e. ≈ +0.007 at this dose.
- **Falsifier.** A live receipt ≤ R0 while `pct_changed` and the band census move as
  designed means the collar carries no new-fault information at this dose: retire the
  collar variant rather than tuning the band to 1 px. A live receipt ≥ +0.010 would
  instead say the SGMC control is the wrong reference for *new* faults — the single
  most useful thing this session could learn, and it would also vindicate the PRUNE
  refills and condemn the `le*` collar-deletion rows.

## `collar20` — `h33-h33-2-b2-CONCENTRATIONcollar20-20261024-106ae19b`

`7,531` dots (20.00 %) moved; band census 4,969 → 12,500 and the >50 px band is
emptied (7,529 → 0); CV 0.6187 → 0.5859, inside the 0.51–0.59 band that the best
historical files reportedly occupy.

- **Hypothesis.** The dose-response is linear in the collar advantage; if the 10 % arm
  is a gain, 20 % is twice the gain.
- **Mechanism.** Same as `collar10`; the extra dose removes *all* mass beyond 50 px,
  which is also the strongest statement of the same bet.
- **Non-fault mimic.** Same mapping-effort confound, plus a new one: an all-collar
  field looks like a "catalogue buffer" file, and the leaderboard cannot distinguish
  "new faults hug traces" from "the scorer rewards proximity to the catalogue". The
  masking rule says the latter cannot pay directly, which is why the bet is on
  adjacent *unmapped* geometry rather than on the catalogue pixels themselves.
- **Predicted live change (MODEL).** **−0.011**, range `[−0.051, +0.008]`. Doubling a
  measured loss doubles the loss; the stored CV only makes it a better-looking file,
  not a better-scoring one.
- **Falsifier.** A receipt ≥ `collar10`'s by +0.010 would mean the collar advantage is
  super-linear (i.e. the near band is genuinely the credit zone); a receipt ≤ −0.010
  closes the collar prior for good and puts the 49 % far-field mass back in the plan as
  the part of R0 that is doing the work.

## `anti10` — `h33-h33-2-b2-CONCENTRATIONanti10-20261024-0e42d6ab`

`3,765` dots (10.00 %) moved the other way: from the weakest collar dots out to
support-weighted cells more than 10 px from the catalogue; band census 4,969 → 1,413;
CV 0.6187 → 0.6312.

- **Hypothesis (the null of this session).** Trace adjacency is worth nothing; the
  credit comes from lineament structure that the independent fault map also sees, and
  that structure lives away from the mapped catalogue.
- **Mechanism.** SGMC-off-catalogue pixels are faults that the competition catalogue
  does not contain — the closest available stand-in for "new fault". A dot placed on a
  support-weighted remote cell sees that kind of truth; a dot hugging a mapped trace
  sees, by construction of the 3 px floor, nothing at all from the mapped trace it
  hugs.
- **Non-fault mimic.** *Distance-for-its-own-sake.* The remote prior grows with
  distance, so part of this arm's SGMC gain is definitional (it moves mass to where
  off-catalogue faults are) and part may be "get away from masked pixels", which would
  not transfer to Phase 2 labels that grow around known traces.
- **Predicted live change (MODEL).** **+0.006**, range `[−0.027, +0.014]`. The only
  positive independent signal in the session (+2.1 % relative on SGMC off-catalogue),
  contradicted by the live-calibrated reference (−0.027 absolute) — i.e. a coin flip
  with a small positive tilt on the only real fault catalogue.
- **Falsifier.** A receipt ≤ R0 retires the "remote structure" story and confirms that
  R0's own far-field dots already capture it (they do, on the lineage reference); a
  receipt ≥ +0.010 says the next session should spend its axis on remote
  support-weighted re-concentration rather than on the collar.

## Instruments, and what they cannot see

- **Catalogue hide-and-recover PROXY** is *identical* for all three arms
  (`0.006186 ± 0.000228`, 5 draws, ≈12,200 withheld positives). That is by
  construction, not a result: acceptors are ≥ 3.05 px from every catalogue pixel, and
  the kernel radius is exactly 3 px, so a moved dot cannot touch a withheld catalogue
  pixel. Same blindness as IR-91-28. The leakage canary reads `0.5` for the same
  reason and carries no information here.
- **SGMC off-catalogue control** is the only independent *fault catalogue*. It cannot
  reward collar placement even if the collar hypothesis is true (a dot at 3.05 px from
  a mapped trace earns exactly zero credit on that trace), and it rewards the mirror
  arm partly by definition. It can compare the two directions; it cannot validate the
  collar alone (IR-91-33).
- **Live-calibrated reference (LCR)** — the lineage field, uniformly subsampled by
  bisection to the density at which R0 scores exactly `0.2778` (s ≈ 0.0412, ≈4,995
  cells, 5 seeded draws). It is the only reference on the live score scale, and it is
  circular for relocation: R0's dots sit on that field's maxima, so *any* move away
  from the field loses credit (all three arms: −0.026 to −0.051). It bounds the
  downside only (IR-91-34).
- **Null diagnostic** (no release, no slot): same donors, same dose, acceptors drawn
  uniformly among legal cells → SGMC −0.66 % relative. So the collar prior is *worse*
  than uniform placement on SGMC, and `anti10` is +2.8 % better than uniform. That
  comparison, not the absolute deltas, is what the session learned.
