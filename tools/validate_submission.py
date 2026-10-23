"""MUST-gates validator for a candidate GEMS raster.

Implements the gate list in the brief (section 6) so a file either passes all gates
or is refused, with a machine-readable receipt. It never estimates a leaderboard
score: proxy numbers are computed only when asked for and are labelled PROXY.

Usage:
    python -m tools.validate_submission \
        --candidate releases/<id>.tif \
        --sample   /path/sample_submission.tif \
        --catalogue /path/catalogue_mask.tif \
        --ledger   ledger/submissions.csv \
        [--parent /path/parent.tif] [--min-gap-px 2.0] [--json receipt.json] \
        [--proxy-truth /path/truth_holdout_mask.tif --proxy-seed 0] \
        [--canary /path/feature.tif]

Exit code 0 = every MUST gate passed. 2 = at least one gate failed. 1 = bad usage
or unreadable input.

Gates
  G1  CRS identical to sample
  G2  shape and transform identical to sample (within 1e-6 relative)
  G3  one band, float32
  G4  values finite and in [0,1] inside the footprint
  G5  non-finite or nodata OUTSIDE the footprint, and zero mass outside
  G6  zero mass on catalogue pixels
  G7  no dot closer than --min-gap-px to a catalogue pixel (default 2.0 = R0 recipe;
      dots in the (min-gap, 3) annulus are reported as a warning, see
      IRREGULARITIES.md item I-3)
  G8  sha256 absent from the ledger, and from every file in releases/
  G9  the file on disk is what was validated: re-read twice, hashes must match
  G10 parent-diff statistics recorded (only when --parent is given)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

BUFFER_ANNULUS_PX = 3.0  # brief 4.4 wants >= 3 px; see I-3


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _transform_tuple(ds) -> tuple[float, ...]:
    t = ds.transform
    return (t.a, t.b, t.c, t.d, t.e, t.f)


def _transforms_equal(a, b, tol: float = 1e-6) -> bool:
    for x, y in zip(a, b):
        scale = max(1.0, abs(x), abs(y))
        if abs(x - y) > tol * scale:
            return False
    return True


def footprint_mask(ds, band: np.ndarray) -> tuple[np.ndarray, str]:
    """Boolean mask of scored pixels, plus how it was determined.

    Preference order:
      1. an explicit nodata value on the dataset;
      2. a sidecar mask band (read by the caller before this function);
      3. finiteness of the sample band (stated assumption, flagged in the receipt).
    """
    if ds.nodata is not None:
        if isinstance(ds.nodata, float) and math.isnan(ds.nodata):
            return np.isfinite(band), "sample:nodata=nan"
        return band != ds.nodata, f"sample:nodata={ds.nodata}"
    return np.isfinite(band), "sample:finite-only(ASSUMPTION)"


def dots_of(values: np.ndarray) -> np.ndarray:
    """Positive-mass pixel coordinates as (N,2) float array of (row, col)."""
    rr, cc = np.nonzero(np.nan_to_num(values, nan=0.0) > 0.0)
    return np.column_stack([rr, cc]).astype(np.float64)


def nearest_distances(points: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Euclidean distance (px) from each point to the nearest True pixel of mask."""
    if not mask.any():
        return np.full(len(points), np.inf)
    # distance transform gives distance TO the nearest zero; invert the mask.
    dist = ndimage.distance_transform_edt(~mask)
    ri = np.clip(np.rint(points[:, 0]).astype(int), 0, mask.shape[0] - 1)
    ci = np.clip(np.rint(points[:, 1]).astype(int), 0, mask.shape[1] - 1)
    return dist[ri, ci]


def displacement_stats(moved: np.ndarray, parent_dots: np.ndarray) -> dict:
    """Nearest-neighbour displacement between two dot sets (px)."""
    if len(moved) == 0 or len(parent_dots) == 0:
        return {"n": int(len(moved)), "mean_px": None, "p95_px": None, "max_px": None}
    from scipy.spatial import cKDTree

    tree = cKDTree(parent_dots)
    d, _ = tree.query(moved, k=1)
    return {
        "n": int(len(moved)),
        "mean_px": float(np.mean(d)),
        "p95_px": float(np.percentile(d, 95)),
        "max_px": float(np.max(d)),
    }


def load_ledger_hashes(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out: set[str] = set()
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            for key in ("sha256", "sha8"):
                v = (row.get(key) or "").strip().lower()
                if v:
                    out.add(v)
    return out


def ledger_hash_hit(sha_full: str, hashes: set[str]) -> str | None:
    for h in (sha_full, sha_full[:8]):
        if h in hashes:
            return h
    return None


def auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Rank AUC via the Mann-Whitney statistic (ties get average rank)."""
    labels = np.asarray(labels).astype(bool)
    n_pos = int(labels.sum())
    n_neg = int((~labels).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), float)
    # average ranks for ties
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        ranks[order[i : j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[labels].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


# --------------------------------------------------------------------------- #
# report-only proxies
# --------------------------------------------------------------------------- #
def proxy_hit_rate(cand: np.ndarray, truth: np.ndarray, seed: int = 0, n_boot: int = 400) -> dict:
    """PROXY: fraction of withheld truth pixels with a dot within 1 px, + 95% CI."""
    pts = dots_of(cand)
    tp = np.argwhere(truth)
    if len(pts) == 0 or len(tp) == 0:
        return {"label": "PROXY", "n_withheld": int(len(tp)), "hit_rate": None, "ci95": None}
    from scipy.spatial import cKDTree

    d, _ = cKDTree(pts).query(tp, k=1)
    hit = d <= 1.0
    rate = float(hit.mean())
    rng = np.random.default_rng(seed)
    boots = [float(rng.choice(hit, size=len(hit), replace=True).mean()) for _ in range(n_boot)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {
        "label": "PROXY",
        "n_withheld": int(len(tp)),
        "hit_rate": rate,
        "ci95": [float(lo), float(hi)],
        "note": "catalogue hide-and-recover proxy; correlates weakly with live score, never a gate",
    }


def canary(feature: np.ndarray, truth: np.ndarray, seed: int = 0, n_bg: int = 5000) -> dict:
    """REPORT ONLY: single-feature AUC; > 0.90 means stop and investigate."""
    rng = np.random.default_rng(seed)
    valid = np.isfinite(feature)
    pos = np.argwhere(truth & valid)
    neg_all = np.argwhere(~truth & valid)
    if len(pos) == 0 or len(neg_all) == 0:
        return {"label": "LEAKAGE-CANARY", "auc": None}
    neg = neg_all[rng.choice(len(neg_all), size=min(n_bg, len(neg_all)), replace=False)]
    s = np.concatenate([feature[tuple(pos.T)], feature[tuple(neg.T)]])
    y = np.concatenate([np.ones(len(pos)), np.zeros(len(neg))])
    a = auc(s, y)
    return {"label": "LEAKAGE-CANARY", "auc": a, "alarm": bool(a == a and a > 0.90),
            "n_pos": int(len(pos)), "n_neg": int(len(neg))}


# --------------------------------------------------------------------------- #
# main validation
# --------------------------------------------------------------------------- #
def validate(
    candidate: Path,
    sample: Path,
    catalogue: Path | None = None,
    ledger: Path | None = None,
    parent: Path | None = None,
    min_gap_px: float = 2.0,
    footprint_path: Path | None = None,
    proxy_truth: Path | None = None,
    feature: Path | None = None,
    seed: int = 0,
    stacklevel_output: bool = True,
) -> dict:
    gates: list[dict] = []

    def gate(name: str, ok: bool, detail: str, **extra):
        gates.append({"gate": name, "pass": bool(ok), "detail": detail, **extra})

    rep: dict = {"candidate": str(candidate), "gates": gates, "warnings": [], "report_only": {}}

    # --- read from disk (G9 uses this too) -------------------------------- #
    sha_a = sha256_file(candidate)
    with rasterio.open(candidate) as ds:
        cand = ds.read(1)
        cand_profile = {
            "crs": str(ds.crs), "shape": [ds.height, ds.width], "count": ds.count,
            "dtype": ds.dtypes[0], "nodata": ds.nodata, "transform": _transform_tuple(ds),
        }
        cand_band_values = cand.copy()
    sha_b = sha256_file(candidate)
    rep["sha256"] = sha_a
    rep["sha8"] = sha_a[:8]
    rep["profile"] = cand_profile
    gate("G9 on-disk identity", sha_a == sha_b, f"re-read sha match: {sha_a == sha_b}")

    # --- sample conformance ---------------------------------------------- #
    with rasterio.open(sample) as sds:
        sample_band = sds.read(1)
        sample_crs = sds.crs
        sample_shape = (sds.height, sds.width)
        sample_transform = _transform_tuple(sds)
        sample_dtype = sds.dtypes[0]
        fp, fp_src = footprint_mask(sds, sample_band)

    if footprint_path is not None:
        with rasterio.open(footprint_path) as fds:
            fpm = fds.read(1)
        if fpm.shape != sample_shape:
            raise ValueError(f"footprint mask shape {fpm.shape} != sample {sample_shape}")
        fp = np.nan_to_num(fpm, nan=0.0) > 0
        fp_src = f"explicit:{footprint_path.name}"

    rep["footprint_source"] = fp_src
    rep["n_footprint_px"] = int(fp.sum())
    if "ASSUMPTION" in fp_src:
        rep["warnings"].append(
            "footprint inferred from sample finiteness: sample_submission.tif has no nodata "
            "value. Confirm the real footprint mask (grid + valid mask) from the competition "
            "page before treating G4/G5 as authoritative."
        )

    gate("G1 CRS", str(sample_crs) == cand_profile["crs"],
         f"sample={sample_crs} candidate={cand_profile['crs']}")
    gate("G2 shape", tuple(cand_profile["shape"]) == tuple(sample_shape),
         f"sample={sample_shape} candidate={tuple(cand_profile['shape'])}")
    gate("G2 transform", _transforms_equal(sample_transform, cand_profile["transform"]),
         f"sample={sample_transform} candidate={cand_profile['transform']}")
    gate("G3 bands", cand_profile["count"] == 1, f"count={cand_profile['count']}")
    gate("G3 dtype", cand_profile["dtype"] == "float32",
         f"sample={sample_dtype} candidate={cand_profile['dtype']}")

    # --- value domain ----------------------------------------------------- #
    v = np.asarray(cand_band_values)
    inside = v[fp]
    finite_inside = np.isfinite(inside)
    gate("G4 finite inside footprint", bool(finite_inside.all()),
         f"{int((~finite_inside).sum())} non-finite pixels inside the footprint")
    if finite_inside.any():
        lo, hi = float(np.nanmin(inside)), float(np.nanmax(inside))
    else:
        lo = hi = float("nan")
    gate("G4 range [0,1]", bool(lo >= 0.0 and hi <= 1.0), f"min={lo:.6f} max={hi:.6f}")
    outside_ok = bool((~np.isfinite(v[~fp])).all()) if (~fp).any() else True
    if cand_profile["nodata"] is not None and not outside_ok:
        outside_ok = bool((v[~fp] == cand_profile["nodata"]).all())
    gate("G5 outside is null", outside_ok,
         "outside-footprint pixels must be NaN (or the declared nodata value)")
    out_mass = float(np.nansum(np.abs(v[~fp]))) if (~fp).any() else 0.0
    gate("G5 zero mass outside", out_mass == 0.0, f"sum|v| outside = {out_mass:g}")

    rep["n_dots"] = int((np.nan_to_num(v, nan=0.0) > 0).sum())
    dots = dots_of(v)

    # --- catalogue gates -------------------------------------------------- #
    if catalogue is not None:
        with rasterio.open(catalogue) as cds:
            cat = cds.read(1)
        cat = np.nan_to_num(cat, nan=0.0) > 0
        if cat.shape != v.shape:
            gate("G6 catalogue shape", False, f"catalogue shape {cat.shape} != candidate {v.shape}")
        else:
            mass_on_cat = float(np.nansum(np.abs(v[cat])))
            gate("G6 zero catalogue mass", mass_on_cat == 0.0,
                 f"sum|v| on {int(cat.sum())} catalogue pixels = {mass_on_cat:g}")
            d = nearest_distances(dots, cat) if len(dots) else np.array([])
            n_viol = int((d < min_gap_px).sum())
            gate(f"G7 gap >= {min_gap_px:g} px", n_viol == 0,
                 f"{n_viol} dots closer than {min_gap_px:g} px to the catalogue")
            n_annulus = int(((d >= min_gap_px) & (d < BUFFER_ANNULUS_PX)).sum())
            rep["catalogue"] = {
                "n_catalogue_px": int(cat.sum()),
                "min_dot_gap_px": float(d.min()) if len(d) else None,
                "n_dots_in_annulus": n_annulus,
            }
            if n_annulus:
                rep["warnings"].append(
                    f"{n_annulus} dots sit in the ({min_gap_px:g}, {BUFFER_ANNULUS_PX:g}) px annulus "
                    "around the catalogue: R0-compatible but below the brief 4.4 wording of >= 3 px "
                    "(IRREGULARITIES.md I-3). Keep or prune deliberately, do not by accident."
                )
    else:
        gate("G6 catalogue gate run", False, "--catalogue not supplied; the zero-mass and gap "
             "gates are mandatory, this run is INCOMPLETE")

    # --- dedupe ----------------------------------------------------------- #
    if ledger is not None:
        hashes = load_ledger_hashes(Path(ledger))
        hit = ledger_hash_hit(sha_a, hashes)
        gate("G8 sha256 not in ledger", hit is None,
             f"ledger match: {hit}" if hit else "no exact-hash repeat in ledger")
        rel = Path("releases")
        if rel.exists():
            dups = [p.name for p in rel.glob("*.tif") if p.stem != candidate.stem and sha256_file(p) == sha_a]
            gate("G8 sha256 unique in releases/", not dups, f"duplicates: {dups}" if dups else "unique")
    else:
        gate("G8 dedupe run", False, "--ledger not supplied; dedupe gate not run")

    # --- parent diff ------------------------------------------------------ #
    if parent is not None:
        with rasterio.open(parent) as pds:
            pv = pds.read(1)
        if pv.shape != v.shape:
            gate("G10 parent diff", False, f"parent shape {pv.shape} != candidate {v.shape}")
        else:
            pf, cf = np.isfinite(pv), np.isfinite(v)
            pz = np.nan_to_num(pv, nan=0.0)
            changed = (~np.isclose(pz, np.nan_to_num(v, nan=0.0), atol=1e-7)) & (pf | cf)
            p_dots, c_dots = dots_of(pv), dots
            added = int(((pv <= 0) & (v > 0)).sum())
            removed = int(((pv > 0) & (v <= 0)).sum())
            rep["parent_diff"] = {
                "n_dots_parent": int(len(p_dots)),
                "n_dots_candidate": int(len(c_dots)),
                "n_px_changed": int(changed.sum()),
                "pct_px_changed": float(100.0 * changed.sum() / max(1, (pf | cf).sum())),
                "n_dots_added": added,
                "n_dots_removed": removed,
                # dot-slot changes: a moved dot counts twice (one vacated, one filled).
                # Divide by 2 for "fraction of parent dots that moved".
                "pct_dot_slots_changed": float(100.0 * (added + removed) / max(1, len(p_dots))),
                "pct_dots_moved": float(50.0 * (added + removed) / max(1, len(p_dots))),
                "parent_displacement_px": displacement_stats(c_dots, p_dots),
            }
            gate("G10 parent diff recorded", True,
                 f"{rep['parent_diff']['pct_px_changed']:.4f}% pixels, "
                 f"{rep['parent_diff']['pct_dots_moved']:.3f}% of dots moved")
    else:
        rep["warnings"].append("no --parent given: parent-diff statistics not recorded (gate G10 skipped)")

    # --- report only ------------------------------------------------------ #
    if proxy_truth is not None:
        with rasterio.open(proxy_truth) as tds:
            truth = tds.read(1) > 0
        rep["report_only"]["hide_and_recover"] = proxy_hit_rate(v, truth, seed=seed)
    if feature is not None:
        with rasterio.open(feature) as fds:
            feat = fds.read(1).astype(np.float32)
        rep["report_only"]["leakage_canary"] = canary(feat, cat if catalogue is not None else fp, seed=seed)

    rep["pass"] = all(g["pass"] for g in gates)
    rep["failed_gates"] = [g["gate"] for g in gates if not g["pass"]]

    if stacklevel_output:
        _print_report(rep)
    return rep


def _print_report(rep: dict) -> None:
    print(f"candidate : {rep['candidate']}")
    print(f"sha256    : {rep['sha256']}  (sha8 {rep['sha8']})")
    print(f"dots      : {rep['n_dots']}   footprint px: {rep['n_footprint_px']}")
    for g in rep["gates"]:
        print(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['gate']:<28} {g['detail']}")
    for w in rep["warnings"]:
        print(f"  [WARN] {w}")
    for k, val in rep["report_only"].items():
        print(f"  [{val.get('label', k)}] {json.dumps(val, default=str)}")
    if "parent_diff" in rep:
        print(f"  parent: {json.dumps(rep['parent_diff'], default=str)}")
    print(f"RESULT    : {'PASS' if rep['pass'] else 'FAIL ' + str(rep['failed_gates'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--sample", required=True, type=Path)
    ap.add_argument("--catalogue", type=Path)
    ap.add_argument("--ledger", type=Path)
    ap.add_argument("--parent", type=Path)
    ap.add_argument("--min-gap-px", type=float, default=2.0)
    ap.add_argument("--footprint", type=Path, help="explicit scored-area mask, edges of truth over sample finiteness")
    ap.add_argument("--proxy-truth", type=Path)
    ap.add_argument("--canary", type=Path)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    for p in [args.candidate, args.sample]:
        if not p.exists():
            print(f"ERROR: missing input {p}", file=sys.stderr)
            return 1
    try:
        rep = validate(
            candidate=args.candidate, sample=args.sample, catalogue=args.catalogue,
            ledger=args.ledger, parent=args.parent, min_gap_px=args.min_gap_px,
            footprint_path=args.footprint,
            proxy_truth=args.proxy_truth, feature=args.canary, seed=args.seed,
        )
    except Exception as exc:  # noqa: BLE001 - usage/IO failure must be loud, not a gate pass
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rep, indent=2, default=str))
        print(f"receipt written: {args.json}")
    return 0 if rep["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
