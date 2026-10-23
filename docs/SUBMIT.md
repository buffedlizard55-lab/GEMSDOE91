# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23 (session 5): three MASS files are built, CERTIFIED and hash-recorded.**
Nothing here submits anything; the human uploads from their own account, one file per slot,
and copies the receipt number back into `ledger/submissions.csv` → `receipt_score` +
`receipt_date`. `releases/*.tif` are gitignored; `releases/MANIFEST.json` is the hash contract.

## Rebuild (≈3 min, eight pinned inputs, every sha256 verified)

```bash
python3 scripts/restore_data.py          # fetch + verify every pinned sha256
python3 scripts/build_mass.py --build    # rebuilds R0 proof + the three MASS arms
python3 scripts/validate_release.py releases/<file>.tif    # must print CERTIFIED
```

The build refuses to run if any input is unpinned, refuses to write if R0 does not come
back exactly from both ancestors, and refuses to record a file that fails a gate.

## The three slot candidates, in plan order

| slot | file | sha256 (check against `releases/MANIFEST.json`) | dots |
|---|---|---|---:|
| 2 | `…-MASSsup10plus-20261023-e23e5141.tif` | `e23e5141…` | 39,023 |
| 3 | *(rebuild)* `R0 & (d_cat > 3)` — see IR-91-18 | 35,483 dots; new hash ≠ `1209e863…` | 35,483 |
| — | `…-MASSsup10minus-20261023-7e7084af.tif` (do not spend a slot) | `7e7084af…` | 31,854 |
| — | `…-MASSsup24minus-20261023-e086e259.tif` (do not spend a slot) | `e086e259…` | 26,672 |

**Slot 1 of the plan is R0 itself**, uploaded unchanged, purely to obtain the receipt that
this lineage has never had. Nothing needs to be built for it.

**Form note** (≤ 140 chars, no score claimed) for `sup10plus`:

```
R0 h33-2-b2 + common 3px collar; add 3540 highest field-rank cells, count 39023; pred -0.002 MODEL
```

## Do not spend a slot on the PRUNE ladder

The PRUNE-extension session's rungs (`le4` `360fe57e`, `le5` `5b6d3987`, `le10` `04002dae`)
are built and CERTIFIED, but measured with the calibrated instrument they are predicted losses
(−0.009 / −0.020 / −0.048). Its slot-1 recommendation (`le10`) is the worst of the six doses
measured. See `SLOT_PLAN.md` and IR-91-19.

## Which encoding

Upload the `.tif` (NaN outside the footprint — spec-literal). Keep the `-zeros.tif` twin as
the rules-allowed fallback, but note: **`validate_release.py` fails the zeros twin on
`nan_outside_footprint` by design** (it passes 13/13 in `gems91.release_gates` with
`zeros_outside_footprint` substituted). No receipt in this lineage has ever confirmed that
the two encodings score identically.

## Format receipt — copy into the PR/session notes

```
candidate: h33-h33-2-b2-20261004-e5eb6e7e-MASSsup10plus-20261023-e23e5141
sha256:    __________________________________________
bytes:     ______
verdict:   CERTIFIED (scripts/validate_release.py, 2026-10-23) — 14/14 gates
```

---

## This session — PRUNE ladder extension (3 files, use one per slot)

All three are delete-only PRUNE (no refill). 14/14 MUST gates PASS.

| # | file to upload (primary NaN) | n_dots | % changed | sha256 (must match `releases/MANIFEST.json`) | bytes |
|---|---|---:|---:|---|---:|
| 1 | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` | 26,294 | 30.17% | `04002dae86db72c3…` | 314,889 |
| 1f| `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae-zeros.tif` (fallback) | 26,294 | 30.17% | `0842d86618dbe64a…` | 174,857 |
| 2 | `h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e.tif` | 33,829 | 10.16% | `360fe57edd828639…` | 348,403 |
| 2f| `h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e-zeros.tif` | 33,829 | 10.16% | `b2c4fa39c78c2f02…` | 204,203 |
| 3 | `h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987.tif` | 32,017 | 14.97% | `5b6d39870bc0fe98…` | 339,956 |
| 3f| `h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987-zeros.tif` | 32,017 | 14.97% | `2ecee55250420948…` | 196,443 |

**Form note** (≤140 chars, per file — no score claimed):

```
Parent R0 h33-h33-2-b2; PRUNE <=10px delete 11360 dots (30.17%), count 26294; pred +0.008 MODEL
Parent R0 h33-h33-2-b2; PRUNE <=4px delete 3825 dots (10.16%), count 33829; pred +0.003 MODEL
Parent R0 h33-h33-2-b2; PRUNE <=5px delete 5637 dots (14.97%), count 32017; pred +0.005 MODEL
```

## Prior session — SPACING (3 files, still available)

| slot rank | file to upload | sha256 (must match `releases/MANIFEST.json`) | bytes |
|---|---|---|---:|
| — | `…-SPACINGspread40-20261023-6d389309-zeros.tif` | `5c517369be3c807c…` | 226,284 |
| — | `…-SPACINGspread40-20261023-6d389309.tif` (NaN-outside primary) | `6d389309aafaa79d…` | 373,103 |
| — | `…-SPACINGclump40-20261023-536d32ad-zeros.tif` (control) | `d393c94f38601567…` | 224,741 |
| — | `…-SPACINGjitter40-20261023-39bb7288-zeros.tif` (null) | `ad6dfa26043f7f19…` | 225,691 |

**Form note** (≤ 140 chars, no score claimed):

```
Parent R0 h33-2-b2; move 15,056 dots (39.99%) 2.0-2.24 px to emptier ground, count fixed 37,654; pred +0.004 MODEL
```

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

## Format receipt — copy this into the PR/session notes (for each file you upload)

```
candidate: h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae
sha256:    04002dae86db72c3fc47652bd66e3ec029e432c909cad779039e9e3749ae0839
bytes:     314889
validate_raster.py: [PASS] crs/shape/transform/dtype/band_count/values_in_0_1/no_nan_inside/nan_outside/zero_catalogue_mass/sha_unseen/reread_from_disk
n_dots:    26294  pct_changed: 30.17%  min_dist_catalogue_px: 10.05

candidate: h33-h33-2-b2-PRUNE-le4-norefill-20261023-360fe57e
sha256:    360fe57edd8286393a180f0ae53c8259899c4344e5bc7f4c4ec20dcdf28530a7
bytes:     348403
n_dots:    33829  pct_changed: 10.16%  min_dist_catalogue_px: 4.12

candidate: h33-h33-2-b2-PRUNE-le5-norefill-20261023-5b6d3987
sha256:    5b6d39870bc0fe9813813f231a56e3b9425e7e2ec149e3e2de8f3ae654b14ce8
bytes:     339956
n_dots:    32017  pct_changed: 14.97%  min_dist_catalogue_px: 5.10
```

Full `validate_raster.py` output is in `evidence/prune_ladder_20261023.json` (gates_text per variant). Paste that block for the file you actually upload; UNVERIFIED is not a pass.

## Format receipt (legacy — prior PRUNE R1 reference)

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


---

## Session 3 — this session's three files, ready to paste

All three are built, gate-clean, and certified by both validators. Upload **one per slot**.

```bash
# re-verify any of them before uploading
python scripts/verify_manifest.py                       # expect PRUNE: READY
python scripts/validate_raster.py releases/R0-PRUNE3-20261023.tif \
    data/official/sample_submission.tif \
    --catalogue data/derived/catalogue_mask.tif --parent \
    data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
python scripts/validate_release.py releases/R0-PRUNE3-20261023.tif \
    --sample data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif --ledger ledger/submissions.csv
```

| # | file | name | note (≤140 chars, counted) |
|---|---|---|---|
| 1 | `releases/R0-PRUNE3-20261023.tif` | `R0-PRUNE3-20261023` | Parent R0 (37654 dots, >=2.2px catalogue). PRUNE <=3px: delete 2171 dots (5.8%), no refill. Predicted +0.002 (-0.002..+0.006). |
| 2 | `releases/R0-PRUNE8-20261023.tif` | `R0-PRUNE8-20261023` | Parent R0. PRUNE <=8px: delete 9164 dots (24.3%), no refill; 3-8px shell has zero catalogue credit. Predicted +0.006 (-0.004..+0.014). |
| 3 | `releases/R0-PRUNE15-20261023.tif` | `R0-PRUNE15-20261023` | Parent R0. PRUNE <=15px: delete 15665 dots (41.6%), no refill; largest dose. Predicted +0.010 (-0.008..+0.024). |

Fallback twins end in `-zeros.tif`; use one encoding per slot, never both.
The parent session's own manifest marked its **zeros** twin `PRIMARY, portal_legal: true`,
so zeros is a proven-acceptable encoding if the uploader objects to NaN.

### Field values

| field | value |
|---|---|
| format receipt | paste the `VERDICT: CERTIFIED` JSON from `validate_release.py` plus the sha256 |
| sha256 (slot 1) | `1209e863a9ff58d86681e9e7f0375c4d185a59c50ef9769f02653ec1472198f2` |
| sha256 (slot 2) | `e1dd69d02b90f95e779c43de1843ac53c4064619e74c81ee230a08058ba15654` |
| sha256 (slot 3) | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` |

### After each score comes back

1. `receipt_score` — the number from the submission page, not a memory of it.
2. `receipt_date` — ISO date; `scripts/ledger.py state` uses it for weekly slot accounting.
3. `status` — `SUBMITTED`.
4. `notes` — if the change was under 0.01, write "no evidence (public chunks only)".

Then update only the CURRENT STATE block in `README.md`.
