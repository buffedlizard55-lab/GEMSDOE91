#!/usr/bin/env python3
"""Nine-site audit (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36): best file, live score, format, relationship.

Every row is produced from bytes and API calls made by this script:
  * the best USER-REPORTED anchor per site comes from ``registry/lfi_live_anchors.csv`` (never typed in by hand);
  * the file path is resolved from the sibling-sweep index or the anchor match file, then **confirmed to exist on the
    site's default branch with the GitHub contents API** (head commit SHA and date are recorded);
  * the raster bytes (restored by ``restore_lfi_anchors.py`` / ``restore_registry.py``) get an automated format check
    against the official sample submission (CRS, shape, affine, dtype, band count, finite values in [0,1]);
  * pairwise relationships between the nine best files are computed exactly (pixel identity, subset, 3-px overlap).

Output: ``docs/s22-xb/nine-sites.json``.  Scores are USER-REPORTED, not organizer receipts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

import sibling_sweep as SS  # noqa: E402  (shared authenticated GitHub API helper; no private fork)

OWNER = "buffedlizard55-lab"
SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
OUT = ROOT / "docs/s22-xb/nine-sites.json"
SAMPLE = ROOT / "data/official/sample_submission.tif"
EXISTING = ROOT / "data/official/existing_faults.tif"
INDEX = ROOT / "data/sibling_sweep/index.tsv"
LOCAL_FALLBACK = {
    "GEMSDOE30": "data/fleet_registry/GEMSDOE30__d28-poisson300m-offcat-44090.tif",
    "GEMSDOE33": "data/fleet_registry/GEMSDOE33__h33d-analog-tip-stepover-r30.tif",
}
SUFFIXES = ("-nan", "-zeros", "_zeros", "-allfinite", "-nanoutside", "-zero", "_nan")


def gh_json(path: str):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def stem(p: str) -> str:
    s = Path(p).name
    for ext in (".tiff", ".tif"):
        if s.lower().endswith(ext):
            s = s[: -len(ext)]
    return s


def format_check(path: Path, ref) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1)
        meta = dict(count=ds.count, dtype=ds.dtypes[0], nodata=ds.nodata, crs=str(ds.crs), shape=list(ds.shape),
                    transform=list(ds.transform)[:6])
    fin = np.isfinite(a)
    inside = ref["footprint"]
    ok_geo = (meta["crs"] == "EPSG:32611" and meta["shape"] == list(ref["shape"]) and
              np.allclose(meta["transform"], ref["transform"]) and meta["count"] == 1 and meta["dtype"] == "float32")
    nan_n = int((~fin).sum())
    nodata_nan = meta["nodata"] is not None and np.isnan(meta["nodata"])
    vals = a[fin]
    in_range = bool(vals.size and vals.min() >= 0.0 and vals.max() <= 1.0)
    binary = bool(np.all((vals == 0) | (vals == 1)))
    nan_inside_footprint = int((~fin & inside).sum())
    # An all-finite file can never trigger "Predicted values must be in range [0, 1]" on NaN; a NaN-outside file is only
    # safe when nodata=NaN is declared (so readers mask it).  Both encodings carried live scores in the user's table.
    if nan_n == 0:
        encoding = "all-finite zeros-outside (recommended)"
    elif nodata_nan:
        encoding = "NaN outside footprint with nodata=NaN declared (matches the official sample)"
    else:
        encoding = "NaN present WITHOUT nodata tag (risk of the [0, 1] range error)"
    pos = (a > 0) & fin
    return dict(meta, ok_geometry=bool(ok_geo), nan_pixels=nan_n, nan_inside_footprint=nan_inside_footprint,
                values_in_0_1=in_range, binary_0_1=binary, n_positive=int(pos.sum()), encoding=encoding,
                positives_on_catalogue=int((pos & ref["catalogue"]).sum()),
                format_pass=bool(ok_geo and in_range and nan_inside_footprint == 0 and (nan_n == 0 or nodata_nan)),
                sha256=sha256(path))


def main() -> int:
    anchors = list(csv.DictReader(open(ROOT / "registry/lfi_live_anchors.csv")))
    matches = {m["name"]: m for m in json.loads((ROOT / "registry/lfi_anchor_matches.json").read_text())}
    index = [l.split("\t") for l in INDEX.read_text().splitlines() if l.strip()]
    index = [r for r in index if len(r) == 4 and r[3] != "-"]

    with rasterio.open(SAMPLE) as ds:
        samp = ds.read(1)
        ref = {"footprint": np.isfinite(samp), "shape": ds.shape, "transform": list(ds.transform)[:6]}
    with rasterio.open(EXISTING) as ds:
        ref["catalogue"] = (ds.read(1) == 1)

    rows, masks = [], {}
    for site in SITES:
        mine = sorted([a for a in anchors if a["site"] == site], key=lambda a: -float(a["user_reported_public_dti"]))
        best = mine[0]
        name, score = best["submission_name"], float(best["user_reported_public_dti"])
        m = matches.get(name, {})
        repo_path = m.get("path")
        if not repo_path:  # strict stem search in the site's own repo
            cand = [r for r in index if r[0] == site and name.split("-2026")[0] in stem(r[1])]
            cand = [r for r in cand if "/downloads/" in "/" + r[1]]
            repo_path = cand[0][1] if cand else None
        local = ROOT / m["local"] if m.get("local") else (ROOT / LOCAL_FALLBACK[site] if site in LOCAL_FALLBACK else None)
        # A row's download link must be the file whose bytes were checked: resolve the repo path by git-blob identity.
        exact_bytes_in_repo = None
        if local is not None and local.is_file():
            data = local.read_bytes()
            blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
            hit = [r for r in index if r[0] == site and r[3] == blob and "/downloads/" in "/" + r[1]]
            if hit:
                repo_path, exact_bytes_in_repo = hit[0][1], True
            else:
                exact_bytes_in_repo = False
        repo_meta = gh_json(f"repos/{OWNER}/{site}") or {}
        branch = repo_meta.get("default_branch", "main")
        head = gh_json(f"repos/{OWNER}/{site}/commits/{branch}") or {}
        on_main = gh_json(f"repos/{OWNER}/{site}/contents/{repo_path}?ref={branch}") if repo_path else None
        row = {
            "site": site, "best_submission_name": name, "user_reported_public_dti": score, "evidence_class": "USER-REPORTED",
            "other_anchors": [{"name": a["submission_name"], "score": float(a["user_reported_public_dti"])} for a in mine[1:]],
            "repo": f"https://github.com/{OWNER}/{site}", "default_branch": branch,
            "head_commit": (head.get("sha") or "")[:12], "head_commit_date_utc": (head.get("commit", {}).get("committer", {}).get("date")),
            "file_path_in_repo": repo_path,
            "checked_bytes_are_this_repo_file": exact_bytes_in_repo,
            "file_exists_on_default_branch": bool(on_main and on_main.get("sha")),
            "raw_download_url": f"https://github.com/{OWNER}/{site}/raw/{branch}/{repo_path}" if repo_path else None,
            "pages_url": f"https://{OWNER}.github.io/{site}/",
            "repo_blob_bytes": on_main.get("size") if on_main else None,
            "repo_blob_git_sha": on_main.get("sha") if on_main else None,
        }
        if local is not None and local.is_file():
            row["local_copy"] = str(local.relative_to(ROOT))
            row["format"] = format_check(local, ref)
            a = rasterio.open(local).read(1)
            masks[site] = np.nan_to_num(a, nan=0.0) > 0.5
        # all-finite "zeros" twin: same repo, same stem with the encoding suffix swapped, pixel-identical dots
        twin = None
        if repo_path and row.get("format") and row["format"]["nan_pixels"] > 0:
            stem0 = stem(repo_path)
            for suf in SUFFIXES:
                if stem0.endswith(suf):
                    stem0 = stem0[: -len(suf)]
            cands = [r for r in index if r[0] == site and "/downloads/" in "/" + r[1]
                     and stem(r[1]) in (stem0 + "-zeros", stem0 + "_zeros", stem0 + "-allfinite")]
            for c in cands:
                tp = ROOT / "data/sibling_sweep/twins" / f"{c[0]}__{Path(c[1]).name}"
                if not tp.is_file():
                    data = SS._api(f"https://api.github.com/repos/{OWNER}/{c[0]}/git/blobs/{c[3]}", "application/vnd.github.raw")
                    if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != c[3]:
                        raise RuntimeError(f"git blob SHA mismatch for twin {c[0]}/{c[1]}")
                    tp.parent.mkdir(parents=True, exist_ok=True)
                    tp.write_bytes(data)
                if tp.is_file():
                    mt = np.nan_to_num(rasterio.open(tp).read(1), nan=0.0) > 0.5
                    twin = {"path_in_repo": c[1], "pixel_identical_dots": bool((mt == masks[site]).all()),
                            "raw_download_url": f"https://github.com/{OWNER}/{site}/raw/{branch}/{c[1]}",
                            "format": format_check(tp, ref)}
                    break
        row["all_finite_twin"] = twin
        rows.append(row)
        print(f"{site}: {score:.4f} exists_on_main={row['file_exists_on_default_branch']} "
              f"format_pass={row.get('format', {}).get('format_pass')}  {name[:60]}", flush=True)

    # exact pairwise relationships among the nine best files
    halos = {s: ndi.distance_transform_edt(~m) <= 3.0 for s, m in masks.items()}  # 3-px halos (<=3 px)
    rel = {}
    for a in SITES:
        for b in SITES:
            if a >= b or a not in masks or b not in masks:
                continue
            ma, mb = masks[a], masks[b]
            inter = int((ma & mb).sum())
            rel[f"{a}|{b}"] = {
                "n_a": int(ma.sum()), "n_b": int(mb.sum()), "common_pixels": inter,
                "identical": bool((ma == mb).all()), "a_subset_of_b": bool((ma & ~mb).sum() == 0),
                "b_subset_of_a": bool((mb & ~ma).sum() == 0),
                "share_of_a_within_3px_of_b": round(float((ma & halos[b]).sum() / max(ma.sum(), 1)), 4),
                "share_of_b_within_3px_of_a": round(float((mb & halos[a]).sum() / max(mb.sum(), 1)), 4),
            }
    # unique-vs-others: the fraction of each file's dots that lie within 3 px of ANY other site's best file
    uniq = {}
    for s in SITES:
        if s not in masks:
            continue
        others = np.zeros_like(masks[s])
        for t in SITES:
            if t != s and t in halos:
                others |= halos[t]
        uniq[s] = {"share_within_3px_of_any_other_of_the_nine": round(float((masks[s] & others).sum() / max(masks[s].sum(), 1)), 4)}
    out = {"audit_date_note": "head commits and file existence queried live via the GitHub API at run time",
           "rows": rows, "pairwise": rel, "uniqueness_among_nine": uniq,
           "rule": "protocol uniqueness: a file is a DUPLICATE if > 70% of its dots lie within 3 px of another raster's dots"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    for s, u in uniq.items():
        print(f"  {s}: {u['share_within_3px_of_any_other_of_the_nine']:.3f} of its dots within 3 px of another site's best file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
