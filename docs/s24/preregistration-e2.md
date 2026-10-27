# S24-CCKM E2 — budget amendment (written after E1, before E2 results)

## What E1 showed (HOLDOUT-DTI, `gems57-pooled-hide-v2`, 60,988 withheld)

- `cckm_e1` 0.045952 [0.037996, 0.054356]; `control_gravgrad` 0.042862;
  `control_kurtcontrast` 0.035739. Paired Δ vs best matched control
  (gravgrad) = +0.003091, 95% CI [−0.004244, +0.010388] — **not significant**.
  The kurtosis-contrast mechanism is not established beyond gravity-gradient
  magnitude; E2 does not change the surface and cannot fix that.
- Surface uniqueness is strong (|ρ|max 0.052 over 115 references); final-dot
  overlap vs the nine focus leaders is 17.2–19.2% (pass), but **100% vs the
  dense calibration lattice** and 76.4% vs a dense union raster — literal
  registry rule failed, as the capacity analysis predicted for any
  geology-driven placement (only 6,649 of 5,167,373 footprint pixels lie
  >3 px from a lattice dot).

## E2 rationale and frozen design

E1 used 20,000 dots solely to stay under the lattice capacity bound (22,163).
E1's lattice overlap was 100% anyway, so that budget sacrifice bought nothing
under the literal rule. The fleet-standard budget of the best historical
family is 37,654 dots (GEMSDOE32 R0, pinned), and with β=0.8 ≫ α=0.2 the DTI
rewards coverage, so budget is the one emission choice with a large expected
paired effect. This was known before E1; it is not surface tuning on E1's
holdout. Ad adaptivity is disclosed regardless: E2 was selected after seeing E1,
so choosing the better of E1/E2 by holdout is a 2-way selection and both
results are reported.

**Frozen for E2:** identical `cckm24.features` surface and constants, identical
folds/evaluator/bootstrap/emitter/collar/spacing; the only change is the dot
budget, 37,654, in every matched arm (`cckm_e2`, `control_gravgrad`,
`control_kurtcontrast`), plus a recomputed 20,000-dot candidate arm
(`cckm_at_20000`) whose pooled HOLDOUT-DTI must reproduce E1's recorded
0.045952… (determinism cross-check). R0 is not re-scored: its emission collar
used the full catalogue (including withheld segments), so on a
hide-and-recover instrument it is structurally handicapped and proved nothing
in E1 (0.006697 is an artefact of that mismatch, not evidence about its
leaderboard behaviour).

Verdict gates are unchanged from E1 (canary; surface; dot-overlap vs **all**
references including the lattice — expected to fail for the geometric reason
above; paired beat-best-matched-control; validator). This is experiment 2 of 3.
No E2 parameter may be changed after its results are seen; hypothesis H2
(granulometry) would need its own preregistration as any E3.
