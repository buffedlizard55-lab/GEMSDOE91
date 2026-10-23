# SLOT PLAN — status after the 2026-10-23 preflight

**This session stopped before building.** The brief requires an exact R0 rebuild and matching
sha256. The pinned NaN/zeros files were retrieved and hash-verified, and the dot set is
reproducible from pinned ancestors, but the original raster bytes cannot be regenerated in
this environment (IR-91-16). No new variant or submission candidate exists. Do not spend a
scoring slot until the human supplies the original byte-reproducible build environment or
confirms a valid alternative parent-identity procedure. The selected axis was PRUNE; all
requested PRUNE values already occur in the ledger, and the refill ranking is missing.

## Next three scored slots (conditional on clearing the parent gate and supplying inputs)

| order | candidate | mechanism / predicted result (MODEL) | what the receipt changes |
|---|---|---|---|
| 1 | MASS `m05drop` | Remove the lowest-ranked 5% using R0's own ranking; predicted small positive, likely <0.01. Requires reproducible rank. | Gain supports excess mass; loss means the lower tail carries recall. |
| 2 | MASS `m05add` | Add the next-ranked 5% from the same parent ranking; count rises by 5%; predicted flat-to-negative. | Opposite-sign contrast distinguishes over-mass from under-mass; if both flat, stop tuning mass. |
| 3 | CONCENTRATION `b25px-m10` | Move 10% from low- to high-prior 25-px blocks (2.5 km), count fixed; report block-density CV before/after. Requires a verified, licensed prior. | Positive ≥0.01 supports block-scale prior transfer; non-positive retires this prior at that scale. |

These are proposed values, not built; check `ledger/submissions.csv` again before construction.
The existing ledger contains MASS m10/m20 and CONCENTRATION b10/b50/15%-prior rows, so those
pairs must not be repeated. The 0.01 threshold applies to interpretation, not as a build gate.

## Weeks to deadline

- **Now / wk 1:** human supplies byte-reproducible R0 recipe/environment and `training_features.tif`; verify every manifest hash, recreate R0 bytes, and only then build slot 1.
- **Wk 2:** use the receipt to decide whether to build slot 2; under |Δ| < 0.01 treat the result as no evidence. Submit no more than three scored candidates in the rolling week.
- **Wk 3–4:** use slot 3 only if its licensed prior is verified and the parent gate still passes; otherwise spend it on a confirmation of the strongest axis.
- **Wk 5–6 / by 2026-12-03 (deadline unconfirmed):** confirm the best result, make a fallback, validate both from disk, and choose one final file blind. No agent submits.

## Better axes to consider later (not built)

1. **MASS-SHAPE at fixed count.** Mechanism: reduce redundant local overlap so dots buy fresh kernel credit without raising total mass. Confounder: genuine fault density is clustered. Falsifier: relocation away from dense clusters lowers live score. Requires a recorded ranking and must be a new (axis,value) pair.
2. **EDGE-FLOOR.** Mechanism: add support only where independent, multi-band geophysical edges agree, rather than snapping every dot to a single-band maximum. Confounder: survey-line / lithologic boundaries mimic faults. Falsifier: no positive live change versus a matched null at the same count. Requires licensed, shareable, hash-pinned bands.

**Human must supply:** byte-reproducible R0 build environment/recipe, the training-features raster and its provenance, TOP_PUBLIC/date, weekly slots remaining, and confirmation of the competition deadline. Do not contact competition or leaderboard pages programmatically.
