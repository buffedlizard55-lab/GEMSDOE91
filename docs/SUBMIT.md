# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23: nothing in this repo is uploadable.** No variant was built
(`IRREGULARITIES.md` IR-91-01/02/04). This page is the exact procedure for the first
slot, which must be run on the machine that holds `data/`.

## Slot 1 — rebuild R1, then submit it

```bash
python src/gems91/pinned.py check                 # 15/15 pins OK
python scripts/preflight.py                       # BUILD ALLOWED
python scripts/validate_release.py releases/<id>.tif --axis PRUNE
```

- **File:** `releases/h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705.tif`
- **sha256 must equal** `6f7ae7052258c509cc83be3851394276e7159324640c98bbcff8e187e1013ec9`
  (zeros twin `dc6f090dd296fcf66ff6e6b5f63a316a5f5eb4ef9cd2ef77edbc73d96f81d36f`).
  If the rebuild does not reproduce that hash, it is a **different file** — log it in
  `IRREGULARITIES.md` and do not call it R1.
- **Form note (103 chars, ≤140):**
  `h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL`
- **Which encoding:** upload the `.tif` (NaN outside footprint, spec-literal). Keep
  `-zeros.tif` as the fallback the rules allow. Note the open risk: **no receipt in this
  lineage has ever confirmed the all-finite `-zeros` encoding is accepted**, so do not
  assume the twins score identically on the organiser's reader — the ledger's line
  "NaN-outside and zeros-outside twins score identically" was never receipt-backed.

## Format receipt — copy this into the PR/session notes

```
candidate: h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705
sha256:    __________________________________________
bytes:     ______
validate_release.py: VERDICT = CERTIFIED      (paste the block; UNVERIFIED is not a pass)
gates: crs/shape/transform/dtype/band_count/values_in_0_1/no_nan_inside/nan_outside/
       zero_catalogue_mass/collar_ge_3px/sha_unseen=UNSEEN(passed)/reread_from_disk
n_dots:    37654      min_dist_catalogue_px: ______
```

## Then, the same day

1. Paste `receipt_score` and `receipt_date` into `ledger/submissions.csv` (never into
   `predicted_change`).
2. If the score moves ≥ +0.01, R1 becomes the parent for every later slot. If it moves
   ≤ −0.01, the 2–3 px shell carries truth and the ≥3 px gate is wrong for this dataset.
3. If |Δ| < 0.01, record it as **no evidence** and proceed on R1 anyway — it is the only
   compliant base.

## Do not

- Do not upload the three MASS variants as progress on MASS: `MASSm10plus` is MODEL −0.010
  and `MASSm20minus` is a nested cut of `MASSm10minus`; both are HOLD upstream, and all
  three inherit R0's 2–3 px collar.
- Do not upload a file whose hash is already in `ledger/submissions.csv` (8+ upstream slots
  were spent on exact repeats), or whose `validate_release.py` verdict is not `CERTIFIED`.
- Do not submit from any account but the one entity's. One final file, chosen blind.
