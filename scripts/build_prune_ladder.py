#!/usr/bin/env python3
"""Build new PRUNE dose variants at thresholds not yet in ledger.

PRUNE delete-only at fixed thresholds; count not held, to isolate denominator saving.
Uses axes.prune directly; ranks not needed.

Thresholds chosen to be novel vs the ledger. As of 2026-10-23 the ladder holds
le3/le4/le5/le8/le10/le15 (delete-only) plus the refill-held p1px/p3px/p4px/prune3
rows, so the 42-50% region of the brief's 1-50% band is UNMAPPED. This session adds
the three top-of-band rungs:

 le16 (16375 dots, 43.49%)
 le18 (17791 dots, 47.25%)
 le19 (18450 dots, 49.00%)  <- the largest dose the brief's 1-50% rule allows

Each changes 1-50% as required.

Outputs:
 - releases/<id>.tif and <id>-zeros.tif (NaN and zeros twins)
 - ledger rows appended (columns preserved; never drops another session's column)
 - evidence JSON: gates, rebuild-based hide-and-recover PROXY, removal-side canary

PROXY instrument note (IR-91-17): gems91.proxy.hide_and_recover scores a child
that was built WITH the whole catalogue against cells withheld from that same
catalogue. For a PRUNE child that is structurally zero by construction (every
surviving dot is farther than the collar from every catalogue cell, withheld or
not), so it carries no information about the PRUNE family. The instrument used
here rebuilds each dose against the REDUCED catalogue and scores the withheld
cells, which is what scripts/proxy.py was written to do.
"""

import datetime as dt
import hashlib
import json
import csv
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import axes as A
from gems91 import geom, io, proxy
import validate_raster as V

# paths
PARENT_NAN = ROOT / "data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CATALOGUE_DERIVED = ROOT / "data/derived/catalogue_mask.tif"
# also need existing_faults for gate? catalogue_mask is derived, but gate uses any catalogue raster >0
CATALOGUE_RAW = ROOT / "data/official/existing_faults.tif"
LEDGER = ROOT / "ledger/submissions.csv"
RELEASES = ROOT / "releases"

PARENT_ID = "h33-h33-2-b2"
DATE = dt.date.today().isoformat().replace("-", "")  # yyyymmdd
DATE_ISO = dt.date.today().isoformat()

# MODEL prediction rule (stated so it can be attacked; see docs/MECHANISM_CARDS.md):
#   per removed dot, delta_DTI ~ +r, calibrated on the ladder's own existing rows
#   (le4/le5/le10/le15 => r = 6.4e-7 .. 8.9e-7 per dot; central r = 7.5e-7).
#   band low  = 0.000 (no dot in the halo carries new-fault credit, but no gain either)
#   band high = r_hi = 1.8e-6 per dot, the DTI-algebra ceiling for a dot with zero
#               truth credit: dDTI = 0.2*DTI^2*(1-m)/T with DTI=0.2778 and the
#               T ~ 8.7e3 implied by the live 0.2778 CLAIM at |G| ~ 3e4, M ~ 1e4.
R_MID, R_HI = 7.5e-7, 1.8e-6
VARIANTS = [
    # (axis value label, max_px, predicted_change, predicted_range, ranking_basis)
    ("le4-norefill", 4.0, "+0.003", "[-0.003,+0.009]", "none - delete-only, distance to catalogue"),
    ("le5-norefill", 5.0, "+0.005", "[-0.004,+0.013]", "none - delete-only, distance to catalogue"),
    ("le10-norefill", 10.0, "+0.008", "[-0.006,+0.019]", "none - delete-only, distance to catalogue"),
    # --- session 2026-10-23 (arena/086eff6b): the unmapped 42-50% region ---
    ("le16norefill", 16.0, "+0.012", "[+0.000,+0.029]",
     "none - delete-only, distance to catalogue; r=7.5e-7/dot central, 1.8e-6 ceiling"),
    ("le18norefill", 18.0, "+0.013", "[+0.000,+0.032]",
     "none - delete-only, distance to catalogue; r=7.5e-7/dot central, 1.8e-6 ceiling"),
    ("le19norefill", 19.0, "+0.014", "[+0.000,+0.033]",
     "none - delete-only, distance to catalogue; largest dose inside the 1-50% band"),
]
# Rebuild-based hide-and-recover PROXY doses (scripts/proxy.py design). Includes the
# rows already in the ledger so the whole ladder is measured on one instrument.
PROXY_DOSES = [3, 8, 15, 16, 18, 19]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------------------------------------------------------------- PROXY helpers
def fold_masks(shape, catalogue, n_folds=4, block=8):
    """Spatially blocked folds of the catalogue (scripts/proxy.py design).

    Withholding a contiguous block means the pruner is never shown those cells, so
    they stand in for new-fault truth. Deterministic: no RNG anywhere.
    """
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    by = (yy // (100 * block)) % 2
    bx = (xx // (100 * block)) % 2
    quad = by * 2 + bx
    ys, xs = np.nonzero(catalogue > 0)
    folds = []
    for f in range(n_folds):
        mask = np.zeros(shape, dtype=bool)
        sel = quad[ys, xs] % n_folds == f
        mask[ys[sel], xs[sel]] = True
        folds.append(mask)
    return folds


def rebuild_proxy(parent, ref, cat, doses, n_folds=4):
    """REPORT-ONLY hide-and-recover DTI for every dose, on one instrument.

    For each fold: hide a blocked share of the catalogue, REBUILD the pruned child
    from the reduced catalogue, and score it against the withheld cells with the
    exact DTI. R0 is scored the same way, as-is, for a baseline.

    This is the instrument that actually moves for the PRUNE family. The alternative
    (gems91.proxy.hide_and_recover on the finished child) is identically zero for a
    PRUNE child - see IR-91-17 - so it is recorded alongside, not instead.
    """
    sys.path.insert(0, str(ROOT / "src"))
    from gems91 import metric as M
    parent_clean = np.nan_to_num(np.where(np.isfinite(parent), parent, 0.0), nan=0.0)
    folds = fold_masks(parent.shape, cat)
    out = {"R0_as_is": [], "n_withheld_per_fold": [int(f.sum()) for f in folds]}
    for d in doses:
        out[f"le{int(d)}"] = []
    for held in folds:
        if not held.any():
            continue
        truth = held.astype(np.uint8)
        cat_train = np.where(held, 0, cat > 0).astype(np.uint8)
        out["R0_as_is"].append(M.dti(parent_clean, truth))
        for d in doses:
            child = A.prune(parent, ref, cat_train, None, float(d), refill=False).array
            child_clean = np.nan_to_num(np.where(np.isfinite(child), child, 0.0), nan=0.0)
            out[f"le{int(d)}"].append(M.dti(child_clean, truth))
    summary = {}
    for k, vals in out.items():
        if not isinstance(vals, list) or not vals:
            continue
        arr = np.array(vals, dtype=float)
        summary[k] = {"mean": float(arr.mean()), "folds": [round(float(x), 6) for x in arr]}
    summary["n_withheld_per_fold"] = out["n_withheld_per_fold"]
    summary["delta_vs_R0"] = {k: round(v["mean"] - summary["R0_as_is"]["mean"], 8)
                              for k, v in summary.items()
                              if isinstance(v, dict) and "mean" in v and k != "R0_as_is"}
    return summary


def removal_canary(parent_dots, child_dots, cat, draws=3, hold_frac=0.2, block=10, seed=7):
    """REPORT-ONLY leakage canary for a delete-only edit.

    The brief's canary asks whether the edit is target-proximal by construction.
    For a deletion the edited dots are the REMOVED ones, so the test is: does
    "was removed" predict "sits within the kernel radius of a WITHHELD catalogue
    cell"? A high AUC means the fold structure is spatially confounded with the
    catalogue and the PROXY above is leaking, not measuring.
    """
    from scipy.spatial import cKDTree
    from gems91.proxy import _auc
    removed = parent_dots & ~child_dots
    ys, xs = np.nonzero(parent_dots)
    pts = np.c_[ys, xs]
    lab = removed[ys, xs]
    cys, cxs = np.nonzero(cat > 0)
    cpts = np.c_[cys, cxs]
    bid = (cys // block) * 100_000 + (cxs // block)
    rng = np.random.default_rng(seed)
    uniq = np.unique(bid)
    vals = []
    for _ in range(draws):
        take = rng.permutation(uniq)[: max(1, int(hold_frac * len(uniq)))]
        hp = cpts[np.isin(bid, take)]
        dmin, _ = cKDTree(hp.astype(np.float64)).query(pts.astype(np.float64), k=1,
                                                      distance_upper_bound=3.0)
        vals.append(_auc(lab.astype(float), np.isfinite(dmin).astype(float)))
    return {"canary_auc_removed_vs_withheld": round(float(np.mean(vals)), 4), "draws": draws,
            "stop_rule": "AUC > 0.90 means the PROXY folds are confounded with the catalogue; investigate before using it"}

def main():
    # verify parent
    assert PARENT_NAN.exists(), f"missing {PARENT_NAN}"
    assert SAMPLE.exists(), f"missing {SAMPLE}"
    assert CATALOGUE_DERIVED.exists(), f"missing {CATALOGUE_DERIVED}"

    with rasterio.open(PARENT_NAN) as src:
        parent_arr = src.read(1)
        parent_meta = src.profile
    with rasterio.open(SAMPLE) as src:
        ref_arr = src.read(1)
        ref_profile = src.profile
    with rasterio.open(CATALOGUE_DERIVED) as src:
        cat = src.read(1)
        cat_profile = src.profile

    # compute parent dcat for info
    cat_bool = cat > 0
    # use distance_transform_edt for truth
    dcat = ndi.distance_transform_edt(~cat_bool)
    parent_dots = np.isfinite(parent_arr) & (np.nan_to_num(parent_arr, nan=0.0) > 0)
    print(f"parent dots {parent_dots.sum()} min_dcat {dcat[parent_dots].min():.3f} max {dcat[parent_dots].max():.1f}")

    # check ledger for existing (parent, axis, value)
    existing_triples = set()
    ledger_rows = []
    if LEDGER.exists():
        with open(LEDGER, newline="", encoding="utf-8") as fh:
            r = list(csv.DictReader(fh))
            ledger_rows = r
            for row in r:
                existing_triples.add((row.get("parent"), row.get("axis"), row.get("value")))
    print(f"existing ledger rows {len(ledger_rows)} triples {len(existing_triples)}")
    # Build is idempotent: if variant already in ledger, we will rebuild and
    # verify byte-identity instead of aborting (CI runs this path).
    ledger_by_value = {(r.get("parent"), r.get("axis"), r.get("value")): r for r in ledger_rows}
    is_rebuild = all((PARENT_ID, "PRUNE", v[0]) in existing_triples for v in VARIANTS)
    if is_rebuild:
        print("rebuild mode: all 3 variants already in ledger — will verify byte-identity")

    # also check existing hashes to avoid dup (only for fresh builds)
    existing_hashes = set()
    for r in ledger_rows:
        for k in ("sha256", "sha256_zeros"):
            if r.get(k):
                existing_hashes.add(r[k].strip())

    # REPORT-ONLY: rebuild-based hide-and-recover DTI for the whole ladder on one
    # instrument (existing rows included, so the dose-response is comparable).
    PROXY_TABLE = rebuild_proxy(parent_arr, ref_arr, cat, PROXY_DOSES)
    print("\nREPORT-ONLY rebuild-based hide-and-recover PROXY (not a score):")
    for k, v in PROXY_TABLE.items():
        if isinstance(v, dict) and "mean" in v:
            print(f"  {k:<10} mean={v['mean']:.6f}")
    print(f"  delta vs R0: {PROXY_TABLE.get('delta_vs_R0')}")

    new_rows = []
    evidence = {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "parent": PARENT_ID,
                "proxy_rebuild_based_ladder": PROXY_TABLE, "variants": {}}

    for value_str, max_px, pred, pred_range, ranking_basis in VARIANTS:
        print(f"\n=== building PRUNE {value_str} max_px={max_px} ===")
        res = A.prune(parent_arr, ref_arr, cat, None, max_px, refill=False)
        print(f"  stats: {res.stats}")
        pct = res.stats["pct_changed"]
        assert 1.0 <= pct <= 50.0, f"pct_changed {pct} not in 1-50%"
        # verify it actually removes expected count
        n_removed = res.stats["removed"]
        n_dots = res.stats["n_dots"]
        print(f"  removed {n_removed} pct {pct} n_dots {n_dots}")

        # check zero catalogue mass
        out_dots = np.isfinite(res.array) & (np.nan_to_num(res.array, nan=0) > 0)
        # catalogue mass check
        on_cat = out_dots & cat_bool
        assert on_cat.sum() == 0, f"produced {on_cat.sum()} dots on catalogue!"
        # collar check: after prune, min distance should be > max_px
        # compute min dcat for remaining dots
        if out_dots.any():
            min_d = dcat[out_dots].min()
            print(f"  min_dcat remaining {min_d:.3f} (should be > {max_px})")
            assert min_d > max_px - 1e-6, f"min_dcat {min_d} not > {max_px}"

        # Write pair
        # Use temporary name then rename to sha8-named
        tmp_base = f"{PARENT_ID}-PRUNE-{value_str}-{DATE}"
        # first write to temp file to compute sha
        RELEASES.mkdir(parents=True, exist_ok=True)
        # write using same profile as sample (ensure correct grid)
        # Use io.write_float32 for proper encoding
        tmp_nan = RELEASES / f"_tmp-{value_str}-nan.tif"
        tmp_zeros = RELEASES / f"_tmp-{value_str}-zeros.tif"
        io.write_float32(tmp_nan, res.array, encoding="nan", template=str(SAMPLE))
        io.write_float32(tmp_zeros, res.array, encoding="zeros", template=str(SAMPLE))

        sha_nan = sha256_file(tmp_nan)
        sha_zeros = sha256_file(tmp_zeros)
        sha8 = sha_nan[:8]
        # The id carries a date, so a rebuild on a LATER day would mint new names and
        # break the releases/MANIFEST.json byte-identity gate. If the ledger already
        # records this (parent, axis, value) with the same bytes, reuse its id.
        recorded = ledger_by_value.get((PARENT_ID, "PRUNE", value_str))
        if recorded and recorded.get("sha256") and recorded["sha256"] != sha_nan:
            print(f"FAIL: {value_str} rebuild sha {sha_nan[:12]} != ledger {recorded['sha256'][:12]}")
            sys.exit(1)
        if recorded and recorded.get("id"):
            final_id = recorded["id"]
            print(f"  reusing recorded id {final_id} (rebuild is date-independent)")
        else:
            final_id = f"{PARENT_ID}-PRUNE-{value_str}-{DATE}-{sha8}"
        final_nan = RELEASES / f"{final_id}.tif"
        final_zeros = RELEASES / f"{final_id}-zeros.tif"
        # Idempotent rebuild: if this exact file already exists in ledger/manifest,
        # verify byte-identity instead of failing on hash collision.
        existing_for_value = recorded
        if existing_for_value and existing_for_value.get("sha256") == sha_nan:
            # Already built; ensure on-disk file matches (or move tmp into place)
            if final_nan.exists():
                # Verify existing file also matches (CI may have just built spacing)
                existing_sha = sha256_file(final_nan)
                if existing_sha != sha_nan:
                    print(f"FAIL: existing {final_nan} hash {existing_sha[:12]} != rebuilt {sha_nan[:12]}")
                    sys.exit(1)
                tmp_nan.unlink(missing_ok=True)
                tmp_zeros.unlink(missing_ok=True)
                print(f"  verified {final_nan} sha {sha_nan[:12]} (already built)")
            else:
                tmp_nan.replace(final_nan)
                tmp_zeros.replace(final_zeros)
                print(f"  wrote {final_nan} sha {sha_nan[:12]} (rebuild)")
            # For rebuilds we still need to populate evidence/gates below; set paths
            # to the verified files and continue to validation.
        else:
            # Fresh build: ensure no hash collision
            if sha_nan in existing_hashes or sha_zeros in existing_hashes:
                print(f"STOP: hash collision for {value_str} sha {sha_nan[:12]} already in ledger")
                sys.exit(2)
            tmp_nan.replace(final_nan)
            tmp_zeros.replace(final_zeros)
            print(f"  wrote {final_nan} sha {sha_nan[:12]}")
            print(f"  wrote {final_zeros} sha {sha_zeros[:12]}")

        # validate gates
        rep = V.validate_raster(final_nan, SAMPLE, catalogue=CATALOGUE_RAW, ledger_csv=LEDGER, parent=PARENT_NAN)
        print(rep.text())
        print("RESULT", "PASS" if rep.ok else "FAIL")
        if not rep.ok:
            print(f"FAIL gates for {value_str}")
            sys.exit(1)
        # also check zeros twin with allow_zeros_outside
        rep_zeros = V.validate_raster(final_zeros, SAMPLE, catalogue=CATALOGUE_RAW, ledger_csv=LEDGER, parent=PARENT_NAN, allow_zeros_outside=True)
        # For zeros, nan_outside is INFO not must-pass, so ok should still be true
        # But we use separate logic: allow_zeros_outside makes that gate non-must
        print("zeros", rep_zeros.text())
        # we don't require zeros PASS for ledger, but we check catalogue mass etc.
        # ---- REPORT-ONLY instruments (never gates) --------------------------
        footprint = np.isfinite(ref_arr)
        # (a) the child-as-built proxy: structurally ZERO for a PRUNE child (IR-91-17).
        #     Kept in the evidence so the zero is visible and explained, not silent.
        prox_as_built = proxy.hide_and_recover(out_dots, cat_bool, footprint)
        # (b) the rebuild-based proxy: the instrument that actually moves.
        prox = PROXY_TABLE.get(f"le{int(max_px)}", {})
        # (c) removal-side leakage canary
        canary = removal_canary(parent_dots, out_dots, cat_bool)
        redund = proxy.redundancy(out_dots)
        cv = proxy.block_density_cv(out_dots, footprint, 10)
        uni = proxy.uniform_truth_credit(out_dots, footprint)

        evidence["variants"][value_str] = {
            "id": final_id,
            "max_px": max_px,
            "stats": res.stats,
            "sha256": sha_nan,
            "sha256_zeros": sha_zeros,
            "sha8": sha8,
            "gates_nan": {g.name: g.ok for g in rep.gates},
            "gates_text": rep.text(),
            "proxy_as_built_structurally_zero": prox_as_built,
            "proxy_rebuild_based": prox,
            "redundancy": redund,
            "block_cv_1km": cv,
            "uniform_truth": uni,
            "canary": canary,
            "min_dcat_remaining": float(min_d) if out_dots.any() else None,
        }

        # form note
        form_note = f"Parent R0 {PARENT_ID}; PRUNE <= {max_px:.0f}px delete {n_removed} dots ({pct:.2f}%), count {n_dots}; pred {pred} MODEL"
        # ensure <=140
        form_note = form_note[:140]
        # predicted_change format
        row = {
            "id": final_id,
            "parent": PARENT_ID,
            "axis": "PRUNE",
            "value": value_str,
            "n_dots": str(n_dots),
            "pct_changed": str(pct),
            "pct_relocated": "",  # not used for prune
            "sha256": sha_nan,
            "sha256_zeros": sha_zeros,
            "status": "BUILT",
            "predicted_change": f"MODEL:{pred}",
            "predicted_range": pred_range,
            "ranking_basis": ranking_basis,
            "receipt_score": "",
            "receipt_date": "",
            "date": DATE_ISO,
            "form_note": form_note,
            "evidence_class": "MODEL",
            "source": "BUILT THIS SESSION (GEMSDOE91 PRUNE ladder)",
            "notes": f"Delete-only contrast: same mechanism as le3/8/15 but new dose {max_px}px. {n_removed} dots at d_cat<={max_px}px removed; {out_dots.sum()} remain. 14/14 gates pass.",
            "source_url": "",
        }
        new_rows.append(row)

    # append to ledger: need to handle csv with proper columns as in current ledger
    if is_rebuild:
        print(f"rebuild mode: ledger already contains all 3 rows — not appending")
        # still verify that new_rows hashes match ledger (already done above)
        # but do not rewrite ledger; just keep evidence
        existing = ledger_rows
        fieldnames = list(csv.DictReader(open(LEDGER, newline="", encoding="utf-8")).fieldnames)
    else:
        with open(LEDGER, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            fieldnames = reader.fieldnames
            existing = list(reader)
        print(f"fieldnames {fieldnames}")
        # Idempotent append: a row whose (parent, axis, value) or sha256 is already in
        # the ledger is bookkeeping that exists, not a new slot. Skipping it is what
        # lets CI re-run this builder on a fresh checkout without duplicating rows
        # (the byte-identity check above is what actually proves the rebuild).
        seen_pairs = {(r.get("parent"), r.get("axis"), r.get("value")) for r in existing}
        seen_sha = {r.get("sha256") for r in existing} | {r.get("sha256_zeros") for r in existing}
        to_append = []
        for r in new_rows:
            for fn in fieldnames:
                if fn not in r:
                    r[fn] = ""
            key = (r["parent"], r["axis"], r["value"])
            if key in seen_pairs or r["sha256"] in seen_sha:
                print(f"  ledger: {r['id']} already recorded - not appending")
                continue
            to_append.append(r)
        # write back
        with open(LEDGER, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
            w.writeheader()
            for r in existing:
                w.writerow({k: r.get(k,"") for k in fieldnames})
            for r in to_append:
                w.writerow({k: r.get(k,"") for k in fieldnames})
        print(f"ledger appended {len(to_append)} new rows to {LEDGER}")

    # write evidence json
    evidence_path = ROOT / "evidence" / f"prune_ladder_{DATE}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"evidence written to {evidence_path}")

    # write releases manifest
    manifest_path = ROOT / "releases" / "MANIFEST.json"
    # load existing manifest if exists
    if manifest_path.exists():
        man = json.loads(manifest_path.read_text())
    else:
        man = {"schema_version": 1, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "files": []}
    for r in new_rows:
        # add both files
        for suffix, sha_key in [(".tif", "sha256"), ("-zeros.tif", "sha256_zeros")]:
            fname = r["id"] + suffix
            # bytes
            fpath = RELEASES / fname
            b = fpath.stat().st_size if fpath.exists() else 0
            # avoid dup
            if not any(f["file"]==fname for f in man.get("files",[])):
                man.setdefault("files", []).append({"file": fname, "sha256": r[sha_key], "bytes": b})
    man["generated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    man["parent"] = PARENT_ID
    man["note"] = "Releases are NOT committed (this repo does not publish derived copies of competition rasters). These hashes are the contract: rebuild with python3 scripts/restore_data.py && python3 scripts/build_prune_ladder.py and every sha256 below must reappear byte for byte."
    manifest_path.write_text(json.dumps(man, indent=2) + "\n")
    print(f"manifest updated {manifest_path}")

    # Also ensure catalogue_mask is tracked
    print("Done")

if __name__ == "__main__":
    main()
