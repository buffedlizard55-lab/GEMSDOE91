# Data handling (merged repository conventions)

The manifest schema is `registry/data_manifest.json` with `schema_version: 1` and a `files`
list. Paths are `local_subpath`, relative to the gitignored `data/` tree. `scripts/preflight.py`
owns the build verdict; `tools/pins.py` is the narrow check a builder makes before it reads
a byte ("is this file one of the pinned inputs?").

## Rules

1. **Nothing is built from memory.** An input is usable only if its sha256 appears in the
   manifest; `tools/pins.check_paths` refuses anything else, and the builder refuses to
   write a raster when it is blocked.
2. **No competition raster is committed.** The repo is public and the data-use terms are
   unchecked. `data/` and `releases/*.tif` are ignored; only recipes, hashes, ledger rows
   and receipts travel.
3. **No automated access to the competition site.** The terms ban it. The human downloads,
   stores and submits; the agent reads local files only.
4. **External data** only if licensed for this challenge and shareable with the sponsor,
   with URL + licence recorded next to the entry. The manifest's `external/` entries are
   the working example.

## What each axis needs (pinned ids)

| axis | pinned ids | why |
|---|---|---|
| CONCENTRATION | `parent_r0_nan`, `existing_faults`, `training_features` | parent dots; collar exclusions; an **external** km-scale prior |
| MASS | `parent_r0_nan`, `training_features` | the parent's own marginal-gain ranking |
| PRUNE | `parent_r0_nan`, `existing_faults`, `training_features` | collar + refill ranking |
| SNAP | `parent_r0_nan`, `existing_faults`, `training_features` | edge/scarp gradients |
| RELIEF | `parent_r0_nan`, `existing_faults`, `training_features` | detrended elevation terciles |
| SPACING | `parent_r0_nan`, `existing_faults` | count-matched relayout |
| TRACKB | `parent_r0_nan`, `existing_faults`, `training_features` | traces + evidence |

Check the current state with:

```bash
python -m tools.pins --axis CONCENTRATION   # every pinned id present and hashed
python scripts/preflight.py                 # the repository-wide verdict: BUILD ALLOWED
```

## Restoring the 419 MB stack (`training_features`)

GitHub refuses blobs over 100 MB, so the competition feature stack is stored as **five
hash-pinned parts** in a sibling repo and reassembled by `scripts/restore_data.py`:

```
data/bridge/gems-geodawn-numerical-features.tif.part-000 … part-004   (each <= 94 MB)
```

Every part is verified against `registry/data_manifest.json → bridge.parts` **before** it is
written, and the concatenation is verified against the whole-file pin `4371c82e…` before it is
moved into place. A swapped or truncated part cannot reach a builder. The five parts are also
public in `6GEMSDOE`, `GEMSDOE` and `GEMSDOE2` — that is a data-use flag, not a convenience
(IRREGULARITIES.md IR-91-17).

## Prior warning (IR-91-07)

For CONCENTRATION the prior must **not** be derived from the parent's own dots. The three
imported CONCENTRATION rows used a 2-block-smoothed parent dot density, which turns the
axis into a clustering edit and cannot test whether an independent prior transfers. Use a
band of `training_features.tif` that was not built from the dot field, or a catalogue
density computed on blocks excluded from the parent's ranking.

## Why the parent hash matters more than it looks

A parent that survived a float64→float32 round trip, a re-compression, or a nodata
re-assignment is a different raster with a different sha256 but visually identical dots.
The verified twins for R0 are `baeae321…` (NaN) and `c55bafc4…` (zeros) — see
`registry/r0_verification.json`; never regenerate them, always fetch and re-hash. The parent's
**bytes** are not re-encodable in this sandbox (IR-91-16), so every artifact also carries a
dot-set digest, and `releases/MANIFEST.json` pins both the sha256 and the dot count per file.
