#!/usr/bin/env python3
"""Broad uniqueness sweep against every published GeoTIFF in the owner's GEMSDOE* repositories.

The protocol registry (registry/*.json, restored by restore_registry.py) is a frozen partial index.
The brief additionally demands a file "unlike any within the GEMSDOE sites". This tool covers that
wider set without pretending it is organizer-complete:

    python scripts/sibling_sweep.py list    > writes data/sibling_sweep/index.tsv (git trees API)
    python scripts/sibling_sweep.py fetch   > downloads every unique blob under */downloads/ that is
                                              < 20 MB and is not a -nan / allfinite twin, verifying
                                              the git blob SHA-1 of every byte stream
    python scripts/sibling_sweep.py check CANDIDATE.tif [--surface S.npy] [--out docs/iso91/sibling-sweep.json]
                                            > directed 3-px dot overlap (literal + chance-corrected + blanket flag),
                                              dots/surface rank correlation, and for DENSE references the
                                              matched-budget (top-K) dot overlap, for every fetched raster

Downloads land in data/ (gitignored); nothing fetched here is ever committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OWNER = "buffedlizard55-lab"
DEST = ROOT / "data" / "sibling_sweep"
INDEX = DEST / "index.tsv"
MAX_BYTES = 20_000_000


def _token() -> str:
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    return tok


def _api(url: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {_token()}", "Accept": accept,
                                               "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def cmd_list():
    DEST.mkdir(parents=True, exist_ok=True)
    repos, page = [], 1
    while True:
        batch = json.loads(_api(f"https://api.github.com/users/{OWNER}/repos?per_page=100&page={page}"))
        if not batch:
            break
        repos += [(r["name"], r["default_branch"]) for r in batch if "gemsdoe" in r["name"].lower()]
        page += 1
    rows = []
    for name, br in sorted(repos):
        try:
            tree = json.loads(_api(f"https://api.github.com/repos/{OWNER}/{name}/git/trees/{br}?recursive=1"))
        except Exception as exc:  # noqa: BLE001 - recorded, not hidden
            rows.append(f"{name}\t#ERROR {exc}\t0\t-")
            continue
        for t in tree.get("tree", []):
            p = t["path"]
            if t["type"] == "blob" and p.lower().endswith((".tif", ".tiff")):
                rows.append(f"{name}\t{p}\t{t.get('size', 0)}\t{t['sha']}")
    INDEX.write_text("\n".join(rows) + "\n")
    print(f"{len(repos)} repositories, {len(rows)} TIFF entries -> {INDEX.relative_to(ROOT)}")


def _selected():
    seen, out = set(), []
    for line in INDEX.read_text().splitlines():
        repo, path, size, sha = line.split("\t")
        if sha == "-" or "/downloads/" not in f"/{path}" or path.endswith("-nan.tif") or "allfinite" in path:
            continue
        if int(size) >= MAX_BYTES or sha in seen:
            continue
        seen.add(sha)
        out.append((repo, path, int(size), sha))
    return out


def cmd_fetch():
    rows = _selected()
    files = DEST / "rasters"
    files.mkdir(parents=True, exist_ok=True)
    ok = bad = skip = 0
    manifest = []
    for repo, path, size, sha in rows:
        dest = files / f"{repo}__{Path(path).name}"
        if dest.exists() and dest.stat().st_size == size:
            skip += 1
            manifest.append(dict(repo=repo, path=path, git_blob=sha, local=str(dest.relative_to(ROOT))))
            continue
        try:
            data = _api(f"https://api.github.com/repos/{OWNER}/{repo}/git/blobs/{sha}", "application/vnd.github.raw")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {repo}/{path}: {exc}", file=sys.stderr)
            bad += 1
            continue
        if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != sha:
            print(f"SHA MISMATCH {repo}/{path}", file=sys.stderr)
            bad += 1
            continue
        dest.write_bytes(data)
        ok += 1
        manifest.append(dict(repo=repo, path=path, git_blob=sha, local=str(dest.relative_to(ROOT))))
    (DEST / "fetched.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"selected {len(rows)} unique blobs: fetched {ok}, already present {skip}, failed {bad}")


def cmd_check(candidate: Path, out: Path | None, surface: Path | None = None):
    """Directed 3-px dot overlap vs every fetched raster, with an explicit dense-reference rule.

    Literal reading (always reported): reference "dots" = every positive pixel. That is degenerate for
    DENSE area rasters (> 3x the candidate's dot count): their 3-px halo covers a large share of the map,
    so the literal 70% bar is met by mere co-location. For dense references the decision therefore uses
    (a) the protocol's rank-correlation rule (surface |Spearman| when ``surface`` is given, and dots
    |Spearman|, both <= 0.90) and (b) for continuous (ranked) rasters the reference's matched-budget dots,
    i.e. its top-K pixels with K = the candidate's dot count, judged by the same 70%-within-3-px bar.
    Sparse references (<= 3K positives) keep the literal rule (blanket ones chance-corrected).
    """
    import rasterio
    from scipy import ndimage as ndi
    from scipy.stats import rankdata
    sys.path.insert(0, str(ROOT / "vendor"))
    from gems57 import grid as G
    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    with rasterio.open(candidate) as ds:
        c = ds.read(1)
    dots = (np.nan_to_num(c, nan=0.0) > 0) & fp
    K = int(dots.sum())
    cy, cx = np.nonzero(dots)
    eligible = fp & ~cat & (ndi.distance_transform_edt(~cat) > 2.0)
    elig_n = int(eligible.sum())
    stride = 5
    fp_idx = np.flatnonzero(fp.ravel())

    def centred_ranks(v):
        r = rankdata(v) - (v.size + 1) / 2.0
        n = float(np.linalg.norm(r))
        return r, n

    rd, rd_n = centred_ranks(dots.ravel()[fp_idx][::stride].astype(np.float64))
    rs = rs_n = None
    if surface is not None:
        sv = np.load(surface).astype(np.float64)
        rs, rs_n = centred_ranks(sv.ravel()[fp_idx][::stride])

    def overlap(ref_mask):
        near = ndi.distance_transform_edt(~ref_mask) <= 3.000001
        fwd = float(near[cy, cx].mean())
        chance = float((near & eligible).sum()) / max(elig_n, 1)
        cov = float((near & fp).sum()) / float(fp.sum())
        corr = (fwd - chance) / (1 - chance) if chance < 1 else 0.0
        return fwd, chance, corr, cov

    cand_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
    manifest = json.loads((DEST / "fetched.json").read_text())
    rows, skipped, seen = [], [], {}
    for m in manifest:
        p = ROOT / m["local"]
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h == cand_sha:
            skipped.append(dict(raster=m["local"], reason="byte-identical to candidate (self)"))
            continue
        if h in seen:
            skipped.append(dict(raster=m["local"], reason=f"same bytes as {seen[h]}"))
            continue
        seen[h] = m["local"]
        try:
            with rasterio.open(p) as ds:
                if ds.count != 1 or ds.shape != fp.shape:
                    skipped.append(dict(raster=m["local"], reason=f"not a single-band competition-grid raster {ds.count}x{ds.shape}"))
                    continue
                a = ds.read(1)
        except Exception as exc:  # noqa: BLE001
            skipped.append(dict(raster=m["local"], reason=f"unreadable: {exc}"))
            continue
        a = np.nan_to_num(a.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        pos = (a > 0) & fp
        n_pos = int(pos.sum())
        row = dict(raster=m["local"], repo=m["repo"], n_positive=n_pos)
        if n_pos == 0:
            row.update(within_3px_literal=0.0, chance=0.0, chance_corrected=0.0, coverage=0.0, blanket=False,
                       dense=False, decision_basis="empty reference", duplicate=False)
            rows.append(row)
            continue
        fwd, chance, corr, cov = overlap(pos)
        blanket = cov >= 0.70
        dense = n_pos > 3 * K
        rr, rr_n = centred_ranks(a.ravel()[fp_idx][::stride])
        dots_rho = abs(float(rd @ rr) / (rd_n * rr_n)) if rr_n > 0 else 0.0
        surf_rho = abs(float(rs @ rr) / (rs_n * rr_n)) if (rs is not None and rr_n > 0) else None
        row.update(within_3px_literal=round(fwd, 5), chance=round(chance, 5), chance_corrected=round(corr, 5),
                   coverage=round(cov, 5), blanket=bool(blanket), dense=bool(dense),
                   dots_abs_spearman=round(dots_rho, 5),
                   surface_abs_spearman=None if surf_rho is None else round(surf_rho, 5))
        literal_flag = (corr if blanket else fwd) > 0.70
        rho_flag = dots_rho > 0.90 or (surf_rho is not None and surf_rho > 0.90)
        if dense:
            vals = a.ravel()[fp_idx]
            n_distinct = int(np.unique(vals[vals > 0][:500_000]).size)
            if n_distinct > 2:
                top = np.argpartition(-vals, K - 1)[:K]
                ref_dots = np.zeros(fp.size, bool)
                ref_dots[fp_idx[top]] = True
                mf, mc, mcorr, mcov = overlap(ref_dots.reshape(fp.shape))
                row.update(matched_budget_within_3px=round(mf, 5), matched_budget_chance=round(mc, 5),
                           matched_budget_chance_corrected=round(mcorr, 5), n_distinct_positive_values=n_distinct)
                dup = rho_flag or mf > 0.70
                basis = "dense continuous: top-K matched-budget dots + rank correlation"
            else:
                dup = rho_flag
                basis = "dense binary area mask: rank correlation (3-px proximity degenerate)"
        else:
            dup = rho_flag or literal_flag
            basis = "sparse: literal 3-px dot overlap (chance-corrected if blanket) + rank correlation"
        row.update(literal_flag=bool(literal_flag), duplicate=bool(dup), decision_basis=basis)
        rows.append(row)
    non_blanket = [r for r in rows if not r["blanket"]]
    sparse = [r for r in rows if not r["dense"]]
    dense = [r for r in rows if r["dense"]]
    worst = lambda rs, k: max(rs, key=lambda r: r.get(k) or 0) if rs else None  # noqa: E731
    report = dict(
        scope=f"every unique */downloads/*.tif (<20 MB, excluding -nan/allfinite twins) in {OWNER}'s GEMSDOE* repositories at sweep time",
        candidate=str(candidate.relative_to(ROOT)) if candidate.is_relative_to(ROOT) else str(candidate),
        candidate_sha256=cand_sha, n_candidate_dots=K, n_compared=len(rows), n_skipped=len(skipped),
        n_dense=len(dense), n_blanket=sum(r["blanket"] for r in rows),
        rule=("duplicate if surface or dots |Spearman| > 0.90, or > 70% of candidate dots within 3 px of the reference's dots; "
              "reference dots = its positive pixels when sparse (<= 3x candidate dots), its top-K pixels (K = candidate dots) when "
              "dense and continuous; dense binary area masks are judged by rank correlation; literal readings always reported"),
        literal_flags=[r["raster"] for r in rows if r.get("literal_flag")],
        max_literal_non_blanket=worst(non_blanket, "within_3px_literal"),
        max_literal_sparse=worst(sparse, "within_3px_literal"),
        max_matched_budget_dense=worst(dense, "matched_budget_within_3px"),
        max_dots_abs_spearman=worst(rows, "dots_abs_spearman"),
        max_surface_abs_spearman=worst(rows, "surface_abs_spearman"),
        duplicates=[r["raster"] for r in rows if r["duplicate"]],
        verdict="DUPLICATE-STOP" if any(r["duplicate"] for r in rows) else "UNIQUE",
        literal_verdict="LITERAL-FLAGS" if any(r.get("literal_flag") for r in rows) else "NO-LITERAL-FLAGS",
        rows=sorted(rows, key=lambda r: -r["within_3px_literal"]), skipped=skipped)
    text = json.dumps(report, indent=1) + "\n"
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
    keys = ("n_compared", "n_skipped", "n_dense", "n_blanket", "literal_verdict", "verdict", "duplicates")
    print(json.dumps({k: report[k] for k in keys}, indent=1))
    for k in ("max_literal_sparse", "max_matched_budget_dense", "max_dots_abs_spearman", "max_surface_abs_spearman"):
        r = report[k]
        if r:
            print(k, {x: r.get(x) for x in ("raster", "n_positive", "within_3px_literal", "matched_budget_within_3px",
                                            "dots_abs_spearman", "surface_abs_spearman")})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("fetch")
    c = sub.add_parser("check")
    c.add_argument("candidate", type=Path)
    c.add_argument("--out", type=Path)
    c.add_argument("--surface", type=Path, help="candidate's continuous surface (.npy) for surface |Spearman|")
    a = ap.parse_args()
    if a.cmd == "list":
        cmd_list()
    elif a.cmd == "fetch":
        cmd_fetch()
    else:
        cmd_check(a.candidate.resolve(), a.out, a.surface)


if __name__ == "__main__":
    main()
