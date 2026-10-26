# Two-slot calibration plan: pin down T, |G| and the matched mass exactly (Session 22)

**Why this exists.** Every projection in this repository is a *model* of the hidden public truth. The score formula is exact, so a few carefully built rasters can turn that model into measurements. Two probe rasters that already exist in the repository (built by GEMSDOE32, SHA-pinned in the registry, **not** built this session) do exactly that for the whole R0 family. **This is a recommendation, not an action: the project never spends a slot.** The files are calibration instruments, not competitive entries; they are derivatives of the 0.2600 raster and are **not unique** under the 70% rule.

## The three rasters (verified from bytes, `docs/s22-xb/probe-predictions.json`)

| Probe | Construction | Status |
|---|---|---|
| S1 | identical to D2.8 (44,090 dots, value 1.0) | **already scored: USER-REPORTED 0.2600 — do not resubmit** |
| **S2** | same 44,090 pixels, every value **0.5** | submit (slot 1) |
| **S3** | D2.8 **plus 2,000 dots**, all inside the footprint, 49.2–167.9 px (median 64.2 px) from the catalogue and ≥ 47.4 px from the H19-5 network | submit (slot 2) |

Files (restored and SHA-verified by `python3 scripts/restore_registry.py --available-only`): `data/fleet_registry/gems32-probe-S2-SCALE-lambda-0.5.tif`, `data/fleet_registry/gems32-probe-S3-NULLADD-2000px.tif`. Both are single-band float32, all-finite, `nodata = None`, so the "[0, 1]" error cannot occur.

## The algebra (exact; unit-tested on synthetic truth in `tests/test_s22_xbreed_lib.py`)

With `DTI = T / (0.2T + 0.2F + 0.8G)` (T = truth credit, F = unmatched dot mass, G = truth size), `λ = 0.5`, `K = 2000`:

```
1/DTI(S2) − 1/DTI(S1) = 0.8 · (G/T) · (1/λ − 1)   ⇒  G/T   (the recall is T/G)
1/DTI(S3) − 1/DTI(S1) = 0.2 · K / T                ⇒  T
F = (T/DTI(S1) − 0.2T − 0.8G) / 0.2
```

`PYTHONPATH=src python3 -c "from gems91.xbreed22 import identify_from_probes as f; print(f(0.2600, S2, S3, lam=0.5, k_null=2000))"`

**Assumption:** the 2,000 added dots are pure false positives. The live-anchored model gives truth density ×5.9 beyond 4 km from the catalogue, so this is *not guaranteed*; S3's own score tests it (below).

## Pre-registered predictions (written before any live score exists)

From the nested-step estimate `T ≈ 5.0–5.5 × 10³` and the matched mass bracketed in `[0, T/2]`:

* **S3: 0.2548 – 0.2551.** Observed > 0.2565 ⇒ the far-field null dots carry credit (T from S3 is then an over-estimate; the far-field is richer than assumed). Observed < 0.2540 ⇒ T is smaller than the nested steps imply.
* **S2: 0.1672 – 0.1738**, depending on |G| (12.1 – 13.4 thousand). The observed value identifies |G|.

## What a result buys

* An *exact* T, |G| and recall for the family that holds every top score on your list, replacing the bracket in `docs/R0_ANALYSIS_S22.md` (|G| ≈ 12.1–13.4 k, recall 38–42%).
* A direct, live test of whether far-field dots are dead weight (S3) — the single most important unknown for deciding where to look for new faults.
* Sharper inputs for `scripts/run_lfi.py`: two more exact equations.

Record the two scores in `registry/lfi_live_anchors.csv`. Cost: 2 of this week's 3 slots (website limit prevails, OFFICIAL forum 11553). If you would rather keep every slot for competitive entries, ignore this plan; nothing else depends on it.
