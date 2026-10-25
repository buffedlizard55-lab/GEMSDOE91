# Data handling (merged repository conventions)

The manifest schema is `registry/data_manifest.json` with `schema_version: 1` and a `files`
list. Paths are `local_subpath`, relative to the gitignored `data/` tree. `scripts/preflight.py`
reports data availability only (not experiment approval); `tools/pins.py` is the narrow check a builder makes before it reads
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
| CONCENTRATION | `parent_r0_nan`, `existing_faults`, `gdr_wellspring_in_footprint`; or `training_features` (Session 8 strain arms) | parent dots; collar exclusions; an **independent** km-scale prior — GDR thermal features (public domain, `training_features` NOT used, IR-91-18) or sponsor geodetic strain bands 4/7/8 (`scripts/build_strain_concentration.py`, digests in `registry/derived_priors.json`) |
| MASS | `parent_r0_nan`, `training_features` | the parent's own marginal-gain ranking |
| PRUNE | `parent_r0_nan`, `existing_faults`, `training_features` | collar + refill ranking |
| SNAP | `parent_r0_nan`, `existing_faults`, `training_features` | edge/scarp gradients |
| RELIEF | `parent_r0_nan`, `existing_faults`, `training_features` | detrended elevation terciles |
| SPACING | `parent_r0_nan`, `existing_faults` | count-matched relayout |
| TRACKB | `parent_r0_nan`, `existing_faults`, `training_features` | traces + evidence |

Check the current state with:

```bash
python -m tools.pins --axis CONCENTRATION   # exit 2 and the missing ids, today
python scripts/preflight.py                 # input availability only
python generate_submission.py --preflight   # separate necessary protocol/capacity checks
```

## Derived priors (IR-91-18)

The CONCENTRATION prior is recomputed, not fetched: `src/gems91/prior.py` turns the pinned GDR
CSV into `exp(-d/12 px)` over de-duplicated Hot/Warm cells, and
`registry/derived_priors.json` records the two digests the builder must reproduce
(`51f294b2…` all features, `6afed3bf…` features >8 px from the catalogue). If a rebuild yields a
different digest, the input changed — stop, do not "fix" the prior.

## Prior warning (IR-91-07)

For CONCENTRATION the prior must **not** be derived from the parent's own dots. The three
imported CONCENTRATION rows used a 2-block-smoothed parent dot density, which turns the
axis into a clustering edit and cannot test whether an independent prior transfers. Use a
band of `training_features.tif` that was not built from the dot field, or a catalogue
density computed on blocks excluded from the parent's ranking.

## Why the parent hash matters more than it looks

A parent that survived a float64→float32 round trip, a re-compression, or a nodata
re-assignment is a different raster with a different sha256 but visually identical dots.
The verified twins for R0 are `caeae…`/`baeae321…` — see `registry/r0_verification.json`;
never regenerate them, always fetch and re-hash.
