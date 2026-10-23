#!/usr/bin/env python3
"""Build three fixed-count PRUNE/H19-cover variants from byte-exact R0.

    python3 scripts/restore_data.py
    python3 scripts/build_prune_refill.py --build

The doses and predictions are read from a preregistration written before any
PROXY or SGMC control is computed.  The script never submits or accesses the
competition site.  Every input is checked against registry/data_manifest.json.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import geom, io, lineage, proxy, release_gates as gates  # noqa: E402
from gems91.pinned import load_manifest, local_path_for, verify_entry  # noqa: E402
from gems91.prune_refill import greedy_support_refill  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"
H195 = DATA / "registry" / "calib_h195_01922.tif"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
PREREG = ROOT / "registry" / "prune_refill_preregistration.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
PRIOR_LEDGER = ROOT / "ledger" / "prior_fleet.csv"
EVIDENCE = ROOT / "evidence" / "prune_refill_axis_20261023.json"
RELEASE_MANIFEST = ROOT / "releases" / "PRUNE_REFILL_MANIFEST.json"
RELEASES = ROOT / "releases"
PARENT_ID = "h33-h33-2-b2"
STAMP = "20261023"
N_DOTS = 37_654
SESSION_SOURCE = "SESSION arena/a52f2ac7 PRUNE-H19COVER"
USED_INPUTS = ("sample_submission", "existing_faults", "parent_r0_nan",
               "parent_r0_zeros", "anc_d2_8", "anc_solo_d2_8", "anc_h19_5",
               "sgmc_faults_control")


def sha256(path: Path) -> str:
    return io.sha256_file(path)


def verify_pins() -> dict:
    manifest = load_manifest(ROOT / "registry" / "data_manifest.json")
    by_id = {entry["id"]: entry for entry in manifest["files"]}
    report = {}
    for fid in USED_INPUTS:
        entry = by_id[fid]
        path = local_path_for(entry, DATA)
        ok, message = verify_entry(entry, path)
        if not ok:
            raise SystemExit(f"PIN FAILURE: {message}; run scripts/restore_data.py")
        report[fid] = {"path": str(path.relative_to(ROOT)),
                       "sha256": sha256(path), "bytes": path.stat().st_size}
    return report


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return list(reader), list(reader.fieldnames or [])


def preflight_pairs(specs: list[dict], rows: list[dict], prior_rows: list[dict]) -> None:
    existing = {(r.get("parent"), r.get("axis"), r.get("value")): r
                for r in rows + prior_rows}
    for spec in specs:
        key = (PARENT_ID, "PRUNE", spec["value"])
        row = existing.get(key)
        if row is not None and row.get("source") != SESSION_SOURCE:
            raise SystemExit(f"Repeated (parent, axis, value): {key}")


def assert_hash_unseen(sha: str, own_id: str, rows: list[dict], prior_rows: list[dict]) -> None:
    for row in rows + prior_rows:
        if row.get("id") == own_id:
            continue
        if sha and sha in {row.get("sha256"), row.get("sha256_zeros")}:
            raise SystemExit(f"Hash already registered for {own_id}: {sha} in {row.get('id')}")


def nearest_neighbour_stats(dots: np.ndarray) -> dict:
    points = np.argwhere(dots)
    distances = cKDTree(points).query(points, k=2)[0][:, 1]
    return {"min_px": round(float(distances.min()), 6),
            "mean_px": round(float(distances.mean()), 6),
            "median_px": round(float(np.median(distances)), 6),
            "p05_px": round(float(np.percentile(distances, 5)), 6),
            "p95_px": round(float(np.percentile(distances, 95)), 6),
            "pairs_below_2px": int((distances < 2.0).sum()),
            "pairs_below_2p8px": int((distances < 2.8).sum())}


def sgmc_control(dots: np.ndarray, control_truth: np.ndarray) -> dict:
    """REPORT-ONLY nearest-dot triangular credit on SGMC-off-catalogue cells."""
    targets = np.argwhere(control_truth).astype(np.float64)
    points = np.argwhere(dots).astype(np.float64)
    distances, _ = cKDTree(points).query(targets, k=1, distance_upper_bound=3.0)
    credit = np.clip(1.0 - np.where(np.isfinite(distances), distances, 3.0) / 3.0,
                     0.0, 1.0)
    return {"evidence_class": "PROXY (SGMC control; not a score)",
            "n_control_positives": int(control_truth.sum()),
            "mean_credit": round(float(credit.mean()), 8),
            "coverage": round(float((credit > 0).mean()), 8)}


def prediction_text(value: float) -> str:
    return f"MODEL:{value:+.3f}"


def range_text(bounds: list[float]) -> str:
    return f"[{bounds[0]:+.3f},{bounds[1]:+.3f}]"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if not args.build:
        print(__doc__)
        return 0

    pins = verify_pins()
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    specs = prereg["variants"]
    rows, fieldnames = read_csv(LEDGER)
    prior_rows, _ = read_csv(PRIOR_LEDGER)
    preflight_pairs(specs, rows, prior_rows)

    lineage_proof = lineage.prove_r0_byte_rebuild(
        parent_nan=PARENT_NAN, parent_zeros=PARENT_ZEROS,
        ancestor_d28=ANC_D28, ancestor_solo=ANC_SOLO,
        sample=TEMPLATE, catalogue=CATALOGUE,
        work_dir=ROOT / "work" / "r0-prune-refill-proof")
    if not lineage_proof["ok"]:
        raise SystemExit(f"STOP: R0 is not reproduced byte-exactly: {lineage_proof}")
    print("R0: both ancestors reproduce the dot set; both TIFF encodings match their pins byte for byte")

    template = io.read_grid(TEMPLATE)
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    support = io.dot_mask(io.read_grid(H195))
    sgmc = io.dot_mask(io.read_grid(SGMC)) & footprint
    sgmc_extra = sgmc & (dcat > 3.0)
    if int(parent.sum()) != N_DOTS or np.any(parent & ~support):
        raise SystemExit("Parent count/support invariant failed")

    r0_proxy = proxy.hide_and_recover(parent, cat, footprint, draws=10, seed=91)
    r0_sgmc = sgmc_control(parent, sgmc_extra)
    r0_nn = nearest_neighbour_stats(parent)
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    git_dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    evidence = {
        "schema": "gems91.prune-h19cover-evidence.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_sha": git_sha, "git_dirty_at_build": git_dirty,
        "seed": {"builder": None, "proxy": 91, "canary": 7},
        "parent": PARENT_ID, "axis": "PRUNE", "fixed_count": N_DOTS,
        "preregistration": {"path": str(PREREG.relative_to(ROOT)),
                            "sha256": sha256(PREREG)},
        "inputs": pins, "lineage": lineage_proof,
        "r0": {"proxy": r0_proxy, "sgmc_control": r0_sgmc,
               "nearest_neighbour": r0_nn,
               "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10)},
        "variants": {},
        "code_sha256": {name: sha256(ROOT / name) for name in (
            "scripts/build_prune_refill.py", "src/gems91/prune_refill.py",
            "src/gems91/lineage.py", "src/gems91/proxy.py")},
        "note": "PROXY and SGMC are report-only, never gates or prediction inputs. Predictions were frozen first.",
    }
    release_records = []
    ledger_rows = []

    for spec in specs:
        threshold = float(spec["threshold_px"])
        survivors = parent & (dcat > threshold)
        removed = parent & ~survivors
        n_add = int(removed.sum())
        if n_add != int(spec["n_removed_expected"]):
            raise SystemExit(f"Dose changed for {spec['value']}: {n_add}")
        pct_changed = 100.0 * n_add / N_DOTS
        if not 1.0 <= pct_changed <= 50.0:
            raise SystemExit(f"Edit fraction out of range: {pct_changed}")
        eligible = support & footprint & ~survivors & (dcat > threshold)
        refill = greedy_support_refill(survivors, support, eligible, n_add,
                                       min_separation_px=None)
        dots = survivors | refill.added
        added = dots & ~parent
        if (int(dots.sum()) != N_DOTS or int(added.sum()) != n_add
                or np.any(dots & cat) or np.any(dots & (dcat <= threshold))
                or np.any(dots & ~support)):
            raise SystemExit(f"Candidate invariant failed for {spec['value']}")

        # Write before naming: the final id contains the actual NaN-file sha8.
        tmp_nan = RELEASES / f"_tmp-prune-{threshold}-nan.tif"
        tmp_zeros = RELEASES / f"_tmp-prune-{threshold}-zeros.tif"
        lineage.write_z9(tmp_nan, dots, footprint, profile_source=CATALOGUE, encoding="nan")
        lineage.write_z9(tmp_zeros, dots, footprint, profile_source=CATALOGUE, encoding="zeros")
        sha_nan = sha256(tmp_nan)
        stem = f"{PARENT_ID}-PRUNE{spec['filename_tag']}-{STAMP}-{sha_nan[:8]}"
        final_nan = RELEASES / f"{stem}.tif"
        final_zeros = RELEASES / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zeros.replace(final_zeros)
        sha_zeros = sha256(final_zeros)
        assert_hash_unseen(sha_nan, stem, rows, prior_rows)
        assert_hash_unseen(sha_zeros, stem, rows, prior_rows)

        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan", floor_px=threshold,
                                       expect_dots=N_DOTS, ledger=LEDGER, own_id=stem)
        g_zeros = gates.validate_release(final_zeros, template=TEMPLATE, catalogue=cat,
                                         encoding="zeros", floor_px=threshold,
                                         expect_dots=N_DOTS, ledger=LEDGER, own_id=stem)
        if not (g_nan["PASS"] and g_zeros["PASS"]):
            raise SystemExit(f"GATE FAIL {stem}: nan={g_nan['failed']} zeros={g_zeros['failed']}")

        variant_proxy = proxy.hide_and_recover(dots, cat, footprint, draws=10, seed=91)
        canary = proxy.canary(added, dots, cat, draws=5, seed=7)
        if np.isfinite(canary["canary_auc"]) and canary["canary_auc"] > 0.90:
            raise SystemExit(f"LEAKAGE CANARY STOP for {stem}: {canary}")
        variant_sgmc = sgmc_control(dots, sgmc_extra)
        diff = gates.parent_diff(parent, dots)
        nn = nearest_neighbour_stats(dots)
        pred = float(spec["predicted_change"])
        bounds = [float(x) for x in spec["predicted_range"]]
        note = (f"R0 h33-2-b2; PRUNE<={threshold:g}px: relocate {n_add} dots "
                f"({pct_changed:.2f}%) to exact-gain H19-5 cells, N=37654; "
                f"pred {pred:+.3f} MODEL")
        if len(note) > 140:
            raise AssertionError(f"Form note too long: {len(note)}")
        record = {
            "id": stem, "parent": PARENT_ID, "axis": "PRUNE", "value": spec["value"],
            "threshold_px": threshold, "threshold_m": threshold * 100.0,
            "n_dots": N_DOTS, "n_removed": n_add, "n_added": int(added.sum()),
            "pct_changed": round(pct_changed, 6),
            "pct_symmetric_difference": round(2.0 * pct_changed, 6),
            "sha256": sha_nan, "sha256_zeros": sha_zeros,
            "bytes": final_nan.stat().st_size, "bytes_zeros": final_zeros.stat().st_size,
            "dot_set_digest": io.dot_digest(dots), "refill_dot_digest": io.dot_digest(added),
            "parent_diff": diff, "refill": refill.stats,
            "removed_catalogue_distance_px": {
                "mean": round(float(dcat[removed].mean()), 6),
                "max": round(float(dcat[removed].max()), 6)},
            "added_catalogue_distance_px": {
                "mean": round(float(dcat[added].mean()), 6),
                "min": round(float(dcat[added].min()), 6)},
            "nearest_neighbour": nn,
            "nearest_neighbour_drift_vs_r0": {k: round(nn[k] - r0_nn[k], 6)
                                               for k in ("mean_px", "median_px", "p05_px")},
            "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
            "proxy": variant_proxy,
            "proxy_delta_vs_r0": round(variant_proxy["proxy_mean_credit"] - r0_proxy["proxy_mean_credit"], 6),
            "leakage_canary": canary, "sgmc_control": variant_sgmc,
            "sgmc_delta_vs_r0": round(variant_sgmc["mean_credit"] - r0_sgmc["mean_credit"], 8),
            "predicted_change": prediction_text(pred), "predicted_range": bounds,
            "hypothesis_preregistered": spec["hypothesis"],
            "form_note": note, "form_note_chars": len(note),
            "gates_nan": g_nan, "gates_zeros": g_zeros,
        }
        evidence["variants"][spec["value"]] = record
        release_records.extend([
            {"file": final_nan.name, "sha256": sha_nan, "bytes": final_nan.stat().st_size},
            {"file": final_zeros.name, "sha256": sha_zeros, "bytes": final_zeros.stat().st_size},
        ])
        ledger_rows.append({
            "id": stem, "parent": PARENT_ID, "axis": "PRUNE", "value": spec["value"],
            "n_dots": N_DOTS, "pct_changed": round(pct_changed, 6),
            "pct_relocated": round(pct_changed, 6),
            "sha256": sha_nan, "sha256_zeros": sha_zeros, "status": "BUILT",
            "predicted_change": prediction_text(pred), "predicted_range": range_text(bounds),
            "ranking_basis": ("fixed-count PRUNE; exact iterative marginal-DTI coverage on pinned H19-5 support outside collar; "
                              "no d2.8 inhibition (infeasible); no live labels"),
            "receipt_score": "", "receipt_date": "", "date": f"{STAMP[:4]}-{STAMP[4:6]}-{STAMP[6:]}",
            "form_note": note, "evidence_class": "MODEL",
            "source": SESSION_SOURCE,
            "notes": (f"Relocate {n_add} dots ({pct_changed:.6f}%); collar {threshold:g}px; count fixed. "
                      f"NN mean {r0_nn['mean_px']:.4f}->{nn['mean_px']:.4f}px (confound). "
                      "Predictions frozen before PROXY/SGMC; no receipt."),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        })
        print(f"{stem}: moved={n_add} ({pct_changed:.4f}%), pred={pred:+.3f} MODEL, "
              f"proxy={variant_proxy['proxy_mean_credit']:.6f}, SGMC={variant_sgmc['mean_credit']:.6f}")

    # Register only after all variants and both encodings have passed every gate.
    existing_ids = {r.get("id") for r in rows}
    for new in ledger_rows:
        old = next((r for r in rows if r.get("id") == new["id"]), None)
        if old is not None:
            if old.get("sha256") != new["sha256"] or old.get("sha256_zeros") != new["sha256_zeros"]:
                raise SystemExit(f"Rebuild hash mismatch for {new['id']}")
        elif new["id"] not in existing_ids:
            rows.append(new)
            existing_ids.add(new["id"])
    for column in ledger_rows[0]:
        if column not in fieldnames:
            fieldnames.append(column)
    with LEDGER.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    RELEASE_MANIFEST.write_text(json.dumps({
        "schema": "gems91.prune-h19cover-release-manifest.v1",
        "generated_utc": evidence["generated_utc"], "git_sha": git_sha,
        "parent": PARENT_ID, "files": sorted(release_records, key=lambda r: r["file"]),
        "rebuild": "python3 scripts/restore_data.py && python3 scripts/build_prune_refill.py --build",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Registered {len(ledger_rows)} variants; evidence={EVIDENCE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
