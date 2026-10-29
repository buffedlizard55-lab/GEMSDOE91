# S26-FABRIC-EMIT — Preregistration (single lane, 3-experiment budget)
**Lane:** S26-FABRIC-EMIT (self-assigned; no supplied method paragraph; reuses S25-FABRIC validated surface). **Source:** `docs/s26/HYPOTHESES.md` H1.

## Hypothesis (single paragraph)
Catalogue-missing buried faults have the same cross-fabric granulometry + gravity/magnetic phase-lag signature as S25-FABRIC, but S25's 3.05 px collar collapsed predictions onto the catalogue halo (median 5.8 px from catalogue, live projection 0.079). Widening the collar to ≥10 px and enforcing distance-stratified quotas plus ≤64% 3-px overlap caps against the four densest competitive families (bhar-e3, spac-e3, h28ridge, cover91) recovers inter-catalogue gaps without re-training the detector. Non-fault mimics: same lithologic contacts, remanent-magnetization offsets, fan/shoreline fabrics, flight-line seams — plus wide alluvial aprons where 10 px still overlaps fan lobes (expected false-positive control).

## Inputs (SHA-pinned)
- `data/official/sample_submission.tif` 2176d08e…
- `data/official/existing_faults.tif` 7ba308cc…
- `data/bridge/gems-geodawn-numerical-features.tif` 4371c82e… (19 bands, B12/B19 for granulometry, B13/B14 for CSPL already validated)
- `data/registry/GEMSDOE32__h33-2-b2-zeros.tif` c55bafc…
- Frozen registry before candidate: `registry/comparison_inventory.json` → `docs/s26/frozen-registry.json`

## Frozen learner, folds, emission
- Learner: **reuse S25-FABRIC E2 full-footprint HGB** (max_iter 300, lr 0.06, max_leaf 63, min_samples_leaf 40, L2 1.0, seed 520810) — no re-tuning.
- Folds: **vendor/gems57/spatial.folds** v3 buffer_px=80 (same instrument as S25; no historical HOLDOUT-DTI is quoted as matched).
- Emission: **new** `gems91.pdwc21.emit_dots_nms` with **collar 10.0 px** (was 3.05), **spacing 3.05 px**, **budget 22 163 dots** (largest geometrically feasible vs lattice; S25 used 37 654) plus distance-quota variant at 37 654 as E2; **competitive cap ≤64%** applied in CELF emitter (S21 precedent). Per-fold budgets proportional to footprint area (S24 protocol).

## Scoring
- `vendor/gems57/evaluate_holdout.py` gems57-pooled-hide-v2 α0.2 β0.8 300 m kernel, 1000 paired block-bootstrap draws, seed 520810. Labels: HOLDOUT-DTI (evaluator, n withheld, 95% CI) vs ORGANIZER-CONFIRMED (receipt).

## Experiments (≤3)
- **E1:** 22 163-dot 10 px collar NMS on S25 E2 full surface (capacity-feasible; passes literal 70% gate if surface is unique).
- **E2:** 37 654-dot 10 px collar NMS on same surface (tests live projection gain at cost of literal blanket; compare to S25 0.079).
- **E3:** 37 654-dot 10 px collar + ≤64% CELF cap vs 4 competitive refs (S21 caps) — only if E2 competitive overlap >70%.

## Duplicate gates
- Pre-approval: surface |ρ| ≤0.90 vs every frozen reference.
- Phase-2: final dots ≤70% within 3 px vs **all** refs including dense blankets (lattice capacity bound recorded). Scopes reported separately: nine leaders, competitive ≤90k px, dense blankets.

## Verdict
`promote` iff canary pass + surface pass + dot pass all scopes + HOLDOUT-DTI beats best matched control (paired CI>0) + validator pass. Else `negative`. `ok_to_submit` mirrors `promote` only; no slot used here.
