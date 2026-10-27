> **Correction — 27 October 2026, later independent review:** this is a
> concurrent historical run, not the new outcome of the current review. The
> checked Band 06 embedded tilt description conflicts with a label-blind
> comparison to a pinned radiometric mirror (`r = 0.996990` on every tenth
> jointly valid pixel); Band 18 also behaves like a signed derivative. Source
> provenance is not independently authenticated. The saved HOLDOUT-DTI cannot
> establish the advertised magnetic-tilt mechanism, and the incumbent
> comparison is not matched or paired; S22's input is contaminated. The S23
> raster is a 99.895% lattice duplicate. Its interior NoData was filled, not
> left as S22's sentinel contamination; the scientific validity of that fill
> remains unproved. **NOT OK TO SUBMIT.** See the
> [current review](../review-8e8d86f2/REVIEW.md),
> [coverage](../review-8e8d86f2/s23-input-audit.json),
> [semantics](../review-8e8d86f2/s23-band-semantics.json), and
> [duplicate witness](../review-8e8d86f2/s23-witness.json). Frozen receipts
> and preregistration below are historical, not revised evidence.

# Three-pass review — S23 TILTA

Branch: `arena/40c331a5-gemsdoe91`. Date: 2026-10-27.

## Outcome first

**OK TO DOWNLOAD: YES — research only. OK TO SUBMIT: NO. Verdict: negative.**

One fresh geophysics-derived TIFF was generated, not copied. Its SHA-256 is new in the competitive indexed scope. It fails the literal dense-lattice duplicate gate (99.90% within 3 px of `calib_r13lattice_00904.tif`) and its HOLDOUT-DTI (0.0148) did not beat the incumbent (0.066223). Zero weekly slots spent.

HOLDOUT-DTI: **0.014803**, 95% CI **[0.011131, 0.018893]**, `gems57-pooled-hide-v2`, **60,988 withheld positives**, pooled 20 km block bootstrap (1,000 draws). Not a leaderboard estimate. Scientific prerequisite (beat incumbent with matched comparison) not satisfied.

## Pass 1 — implement and measure

- Read standing README, prior next steps, source modules, shared template, registry policy, historical forensics.
- Restored SHA-pinned sample, catalogue, 19-band stack, and parent R0 from immutable GitHub mirrors; verified hashes.
- Restored 62/64 frozen references (2 quarantined local artifacts missing, disclosed).
- Preregistered 5 hypotheses and one fixed TILTA experiment; used only B06/B18, avoiding disputed band semantics.
- Reused shared spatial folds, canary logic, `evaluate_holdout.py`, NMS emitter, `submission_writer.py`. No private metric fork.
- Tested 6 raw/derived features × 4 folds; max symmetric AUC 0.6134 PASS.
- Checked 114 pre-placement surfaces; max |Spearman| 0.041 PASS.
- Produced holdout (20k budget, 3.05 px collar/spacing), serialized TIFF+ZIP via shared writer, re-read bytes.
- Nine-site audit frozen unchanged; all nine leaders ≥84.7% overlap vs another, GEMSDOE25/30 identical support.

## Pass 2 — bugs, edge cases, historical contradictions

- Fixed sentinel handling: GeoDAWN bands contain `-3.4e38` sentinel inside footprint; cleaning to NaN then nearest-neighbor fill prevents nonfinite leakage.
- Fixed SurfaceProbe API misuse (`candidate, footprint` not `footprint` alone) and tilt alignment overflow.
- Fixed `write_submission` signature (requires sample, footprint, note, name, catalogue).
- Corrected competitive vs literal uniqueness: competitive (≤90k dots) max ~20% PASS; literal dense 99.9% FAIL disclosed as capacity bound, not silently exempted.
- Reconciled leaderboard snapshots: 0.4413/0.3195 are earlier observations; 2026-10-26 fetch was 0.4437/#1, 0.2826/#50 — not receipts for our raster.
- Noted tilt/grav alignment squared cosine can be zero in low-gradient areas; product ensures fault-specific boost but may suppress isolated edges — acceptable for negative result.

## Pass 3 — final verification checklist

- `python scripts/restore_data.py --only sample_submission,existing_faults,training_features` — OK
- `python scripts/restore_registry.py --available-only` — 62/64 verified
- `python scripts/run_s23_tilta.py` — produced 20,000 dots, holdout 0.0148, canary PASS, surface PASS, final literal FAIL (expected), competitive PASS
- `python generate_submission.py --with-data` — portal front-door still points to S22 OMTJ (renderer separate); new artifact validated via `docs/s23/writer-receipt.json`
- `python -m pytest -k "not integration"` — 695 passed (prior S22 evidence)
- TIFF: 1-band float32, EPSG:32611, 3730×3292, transform matches sample, all finite in [0,1], nodata=None, zero on catalogue, SHA new
- ZIP: single-TIFF, readable

No claim that this session achieved higher leaderboard result. Objectives remain blocked by negative holdout and literal duplicate impossibility.

## Exact reproducibility

```bash
python -m pip install --break-system-packages -r requirements.txt
python scripts/restore_data.py --only sample_submission,existing_faults,training_features,parent_r0_zeros
python scripts/restore_registry.py --available-only
python scripts/run_s23_tilta.py
```

The run is immutable: `docs/s23/run-card.json` refuses overwrite. Re-validate bytes:

```bash
python scripts/verify_s23.py --with-data  # if implemented
python -m pytest
```

Do not rerun in same workspace to claim new experiment; use separate approved workspace.

## Next session

Resolve dense-reference feasibility with coordinator; rerun matched incumbent with equalized budgets and paired bootstrap; verify 3DEP 1 m LiDAR ingest on unrestricted host; record authenticated receipts; maintain renderer-owned `docs/current-run.json`.
