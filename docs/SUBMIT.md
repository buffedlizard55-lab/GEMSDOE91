# SUBMIT — what to upload, and what to paste back

**Status 2026-10-23 (session 4): the MASS/consensus arms are built, gate-clean and certified by
every §6 MUST gate — they are the current slot candidates (section below). **The §4.4 collar is
inherited from R0 and cannot be cleared without turning a file into a PRUNE arm (IR-91-03); the
human must rule on that before uploading.** The PRUNE and SPACING files described further down
are still rebuild-on-demand and unchanged.**
**Nothing has ever been submitted by an agent, and no agent may submit.** One file per slot;
the `-zeros` twin is the fallback, not an extra entry.

---

## SESSION 4 — MASS/consensus: the three files to upload (one per slot)

```bash
python3 scripts/restore_data.py                 # fetch + verify every pinned sha256
python3 scripts/make_catalogue.py               # rebuild the mask; must hash to c97c7819…
python3 scripts/build_mass_consensus.py         # writes the 3 pairs under releases/, ~20 s
python3 scripts/validate_raster.py releases/<file>.tif data/official/sample_submission.tif \
    --catalogue data/official/existing_faults.tif \
    --parent data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif
python3 scripts/validate_release.py releases/<file>.tif --axis MASS
```

Rebuilds are deterministic (no RNG anywhere) and were verified to reproduce the hashes below.

| slot | file | sha256 (NaN-outside) | zeros twin | bytes (NaN) |
|---|---|---|---|---|
| **1** | `h33-h33-2-b2-MASScons3add-20261023-2803126d.tif` | `2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd` | `597d6d0e…` | 384,079 |
| **2** | `h33-h33-2-b2-MASScons1drop-20261023-fc8f5500.tif` | `fc8f5500790eed45fe4957a3a548c55513db09774ecd46c300b67b4cc72d854e` | `9f24d22e…` | 354,433 |
| 3 (only if 1–2 flat) | `h33-h33-2-b2-PRUNEle15norefill-20261023-1ca1ff6f.tif` | `1ca1ff6f782d5ba3c95ec1f9b70b029359b636b826d69316d6e9c60f740dafd0` (rebuild first) | — | — |
| keep | `h33-h33-2-b2-MASScons2drop-20261023-e8871e7f.tif` | `e8871e7f7bd75b139173e2c93eda3a79f47063e6e71dd4dfef7672cf58c4662f` | — | 328,675 |

**Form notes** (≤140 chars each, no score claimed, counted):

```
1: h33-2-b2; +3765 dots (10.0%) at 3-of-3 cross-field support cells, >=3px off catalogue; pred +0.009 MODEL
2: h33-2-b2; -4541 single-support dots (12.1%), count 33113, whole stratum; pred -0.000 MODEL
3: h33-2-b2; delete-only <=15px collar, 21989 dots, no refill; pred +0.010 MODEL
```

**Format receipt — paste this back with the score:**

```
candidate: h33-h33-2-b2-MASScons3add-20261023-2803126d
sha256 (NaN)    : 2803126de23b7f3388d2d4db727c2e8a39b499308b6efc61941d4231606f9abd
sha256 (zeros)  : 597d6d0ea528c8630e301dfe354b62905534d49f985f5bd92f04a75e51d7e5cf
n_dots          : 41419        min_dist_catalogue_px: 2.236  (inherited from R0, IR-91-03)
validate_raster.py  : 14/14 PASS (§6 MUST gates)
validate_release.py : 14 MUST gates PASS; collar_ge_3px FAIL = inherited, R0 fails it identically (2171 dots, IR-91-03)
CRS EPSG:32611 | 3730x3292 | 100 m | float32 | 1 band | values {0,1} | NaN outside
zero catalogue mass: 0 px        ledger sha: new at build time
```

**Known wrinkle, stated up front:** all three arms inherit R0's 2,171 dots at 2–3 px from the
catalogue, so the brief's "≥3 px unless PRUNE" is violated by the parent itself, not by the edit
(IR-91-03). The new mass in slot 1 is ≥3 px by construction. If the human prefers a compliant
parent, rebase on `PRUNEle3norefill` (35,483 dots) instead — but then the file is a two-change
build and must not be described as a MASS-only arm.

---
 (`releases/`, rebuilt on demand —
`releases/*.tif` are gitignored, the sha256 contract is `releases/MANIFEST.json`).
**Nothing has ever been submitted by an agent, and no agent may submit.** One file per slot;
the `-zeros` twin is the fallback, not an extra entry.

## Rebuild first (10–40 s, five inputs, all hash-verified)

```bash
python3 scripts/restore_data.py           # fetch + verify every pinned sha256
python3 scripts/build_spacing.py --build  # rebuild the parent proof and all three arms
python3 scripts/validate.py releases/<file>.tif   # must print PASS
```

The build refuses to proceed unless R0's dot set is reproduced exactly from both pinned
ancestors, and refuses to write the ledger unless every release passes every hard gate.

## Session-3 files

| slot rank | file to upload | sha256 (must match `releases/MANIFEST.json`) | bytes |
|---|---|---|---:|
| 2 | `…-SPACINGspread40-20261023-6d389309-zeros.tif` | `5c517369be3c807c…` | 226,284 |
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
