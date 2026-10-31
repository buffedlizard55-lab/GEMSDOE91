"""S28: byte-level forensics of the nine focus-site leader rasters.

Every number produced here is re-derived from the raster bytes retrieved through
the GitHub Blob API at the commit pinned in
``docs/review-20261030/nine-site-snapshot.json``.  The SHA-256 of each retrieved
file is checked against the pin before any statistic is computed; a mismatch is
a hard failure.

Statistics computed (all on the official competition grid):

* shape / dtype / value range / positive-pixel count / positive mass
* distance-to-catalogue histogram (px, 100 m cells)
* nearest-neighbour spacing between predicted dots
* directed pairwise overlap: share of A's dots that lie within 3 px of a B dot
  (the parallel-run protocol's 70 % stop statistic; peer-only, not full registry)
* the distance-weighted-Tversky algebra of the reported score solved against a
  common hidden-truth size, so the reported numbers can be checked for internal
  consistency instead of being taken on trust.

Nothing here is a score.  Reported scores are labelled USER-REPORTED.
"""
from __future__ import annotations

import json
import tarfile
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
SNAP = ROOT / "docs" / "review-20261030" / "nine-site-snapshot.json"
OUT = ROOT / "docs" / "s28"
CACHE = ROOT / "data" / "nine_site_raster"

ALPHA, BETA, R = 0.2, 0.8, 3.0


def load_grid():
    from vendor.gems57.grid import load_grid as _load

    return _load(ROOT / "data" / "official")


def fetch(site: dict) -> Path:
    """Retrieve one pinned raster once, verifying SHA-256."""
    import subprocess

    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / site["reported_file"]
    if p.exists() and p.stat().st_size == site["bytes"]:
        import hashlib

        if hashlib.sha256(p.read_bytes()).hexdigest() == site["sha256"]:
            return p
    if p.exists():
        p.unlink()
    url = f"https://api.github.com/repos/{site['repository_owner']}/{site['repository_name']}/git/blobs/{site['git_blob_sha']}" \
        if site.get("git_blob_sha") else None
    if url is None:
        # resolve the commit-pinned blob through the trees API
        tree = subprocess.run(
            ["gh", "api", f"repos/{site['repository_owner']}/{site['repository_name']}/git/trees/{site['commit']}?recursive=1"],
            capture_output=True, text=True, check=True).stdout
        entries = {e["path"]: e["sha"] for e in json.loads(tree)["tree"]}
        url = f"https://api.github.com/repos/{site['repository_owner']}/{site['repository_name']}/git/blobs/{entries[site['repository_path']]}"
    tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["curl", "-sSL", "-H", f"Authorization: token {tok}",
                    "-H", "Accept: application/vnd.github.raw", "-o", str(p), url], check=True)
    import hashlib

    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != site["sha256"]:
        raise RuntimeError(f"{site['reported_file']}: sha256 {got} != pinned {site['sha256']}")
    return p


def read_tif(path: Path):
    import rasterio

    with rasterio.open(path) as ds:
        a = ds.read(1)
        return a, dict(crs=str(ds.crs), shape=[ds.height, ds.width], dtype=ds.dtypes[0])


def dot_stats(a: np.ndarray, cat: np.ndarray, fp: np.ndarray) -> dict:
    pos = a > 0
    n = int(pos.sum())
    yy, xx = np.nonzero(pos)
    finite = np.isfinite(a)
    vals = a[finite]
    out = dict(
        positive_pixels=n,
        positive_mass=float(np.nansum(np.where(finite, a, 0))),
        binary=bool(np.all((vals == 0) | (vals == 1))),
        min=float(vals.min()) if vals.size else None,
        max=float(vals.max()) if vals.size else None,
        nan_cells=int(np.isnan(a).sum()),
        inside_footprint=int((pos & fp).sum()),
        on_catalogue=int((pos & cat).sum()),
    )
    if n:
        dcat = ndi.distance_transform_edt(~cat)
        d = dcat[pos]
        out["dcat"] = dict(
            median_px=float(np.median(d)),
            mean_px=float(d.mean()),
            p90_px=float(np.percentile(d, 90)),
            frac_le1=float((d <= 1).mean()),
            frac_le2=float((d <= 2).mean()),
            frac_le3=float((d <= 3).mean()),
            frac_gt10=float((d > 10).mean()),
        )
        # nearest-neighbour spacing among dots (two-pass EDT is exact enough for
        # the 1-10 px range we care about; verified against cKDTree below)
        from scipy.spatial import cKDTree

        pts = np.column_stack([yy, xx]).astype(np.float32)
        if n > 1 and n <= 400_000:
            tree = cKDTree(pts)
            dd, _ = tree.query(pts, k=2)
            nn = dd[:, 1]
            out["nn_spacing_px"] = dict(median=float(np.median(nn)), mean=float(nn.mean()),
                                        p10=float(np.percentile(nn, 10)), p90=float(np.percentile(nn, 90)))
        out["points"] = np.column_stack([yy, xx])
    return out


def directed_overlap(pa: np.ndarray, pb: np.ndarray, r: float = R) -> float:
    """Share of A's dots within r px (Euclidean) of any B dot."""
    from scipy.spatial import cKDTree

    if pa.shape[0] == 0 or pb.shape[0] == 0:
        return float("nan")
    d, _ = cKDTree(pb).query(pa, k=1)
    return float((d <= r).mean())


def tversky_algebra(score: float, n_dots: int, truth_sizes=(15_000, 25_000, 40_000)) -> dict:
    """Solve TP_w for a reported DTI given candidate hidden-truth sizes.

    DTI = T / (T + ALPHA*FP + BETA*K), FP = n_dots - M, and M <= min(n_dots, ...).
    We report the *feasible* T implied at M = T (near-bijection, the optimistic
    case) so the implied hit-rate T/K can be compared across sites.
    """
    out = {}
    for k in truth_sizes:
        # assuming M = T (each dot has nearby truth credit equal to mean truth credit)
        t = score * (ALPHA * n_dots + BETA * k) / (1.0 - ALPHA * score)
        out[str(k)] = dict(TP_w=t, hit_rate_per_dot=t / n_dots, recall=t / k)
    return out


def main() -> int:
    snap = json.loads(SNAP.read_text())
    grid = load_grid()
    cat, fp = grid.catalogue, grid.footprint
    print(f"grid: footprint={int(fp.sum())} catalogue={int(cat.sum())}")

    rows = []
    for s in snap["sites"]:
        p = fetch(s)
        a, meta = read_tif(p)
        st = dot_stats(a, cat, fp)
        rows.append(dict(site=s["site"], file=s["reported_file"], sha256=s["sha256"],
                         bytes=s["bytes"], reported_user=float(s["reported_public_dti"]),
                         meta=meta, **{k: v for k, v in st.items() if k != "points"}))
        rows[-1]["_points"] = st.get("points")
        print(s["site"], rows[-1]["positive_pixels"], rows[-1]["dcat"]["median_px"],
              rows[-1]["nn_spacing_px"]["median"] if "nn_spacing_px" in rows[-1] else None)

    # pairwise overlap matrix
    matrix = {}
    for i, ri in enumerate(rows):
        for j, rj in enumerate(rows):
            if i == j:
                continue
            matrix[f"{ri['site']}->{rj['site']}"] = directed_overlap(ri["_points"], rj["_points"])
    for r in rows:
        peers = {k.split("->")[1]: v for k, v in matrix.items() if k.startswith(r["site"] + "->")}
        worst = max(peers.items(), key=lambda kv: kv[1])
        r["max_peer_overlap_3px"] = worst[1]
        r["closest_peer"] = worst[0]
        r["unique_within_nine_at_70pct"] = bool(worst[1] < 0.70)
        r["algebra"] = tversky_algebra(r["reported_user"], r["positive_pixels"])
        r.pop("_points")

    OUT.mkdir(parents=True, exist_ok=True)
    payload = dict(
        schema="gems91.s28.nine-site-forensics.v1",
        generated_utc=__import__("datetime").datetime.utcnow().isoformat() + "Z",
        method="SHA-256 verified GitHub Blob retrieval at pinned commits; all statistics recomputed from bytes on the official grid",
        evidence_class="reported scores are USER-REPORTED (no organizer receipt was available); geometry statistics are VERIFIED-FROM-BYTES",
        grid=dict(footprint_pixels=int(fp.sum()), catalogue_pixels=int(cat.sum())),
        sites=rows, overlap_matrix=matrix,
    )
    (OUT / "nine-site-forensics.json").write_text(json.dumps(payload, indent=1, default=float))
    print("wrote", OUT / "nine-site-forensics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
