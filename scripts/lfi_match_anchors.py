#!/usr/bin/env python3
"""Match USER-REPORTED live anchors (registry/lfi_live_anchors.csv) to published GeoTIFFs.

Source of rasters: data/sibling_sweep/index.tsv (git trees API listing of every GEMSDOE* repo,
written by scripts/sibling_sweep.py list). Each match is fetched by git blob SHA-1 and verified.
Matching is deliberately strict and fully logged; ambiguous or missing names are reported, never guessed:
  rule 1  the file stem equals the submission name (after stripping .tif/.zip)
  rule 2  the file stem equals the name with one encoding suffix added/removed (-nan, -zeros, _zeros,
          -allfinite, -nanoutside)
  rule 3  the file stem contains the full name (only accepted when every hit has the same blob SHA)
Candidates are restricted to the anchor's own site repository first; other repos only if none found.
"""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sibling_sweep as SS  # reuse authenticated API helper (no private fork)

INDEX = ROOT / "data/sibling_sweep/index.tsv"
DEST = ROOT / "data/lfi_anchors"
OUT = ROOT / "registry/lfi_anchor_matches.json"
SUFFIXES = ("-nan", "-zeros", "_zeros", "-allfinite", "-nanoutside", "-zero", "_nan")


def stem(p: str) -> str:
    s = Path(p).name
    for ext in (".tiff", ".tif"):
        if s.lower().endswith(ext):
            s = s[: -len(ext)]
    return s


def variants(name: str) -> set[str]:
    out = {name}
    for suf in SUFFIXES:
        out.add(name + suf)
        if name.endswith(suf):
            out.add(name[: -len(suf)])
    return out


def main() -> None:
    rows = [l.split("\t") for l in INDEX.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if len(r) == 4 and r[3] != "-"]
    anchors = list(csv.DictReader(open(ROOT / "registry/lfi_live_anchors.csv")))
    DEST.mkdir(parents=True, exist_ok=True)
    results = []
    for a in anchors:
        name, site = a["submission_name"], a["site"]
        rec = dict(site=site, name=name, score=float(a["user_reported_public_dti"]),
                   evidence_class="USER-REPORTED", site_url=a["site_url"])
        hit, rule = [], None
        for pool_name, pool in (("own-repo", [r for r in rows if r[0] == site]), ("any-repo", rows)):
            v = variants(name)
            h1 = [r for r in pool if stem(r[1]) == name]
            h2 = [r for r in pool if stem(r[1]) in v]
            h3 = [r for r in pool if name in stem(r[1])] if len(name) >= 12 else []
            for h, rl in ((h1, "rule1"), (h2, "rule2"), (h3, "rule3")):
                if h and len({r[3] for r in h}) == 1:
                    hit, rule = h, f"{rl}/{pool_name}"
                    break
                if h and rl != "rule3":
                    # several distinct blobs with an exact stem: prefer docs/downloads
                    dl = [r for r in h if "/downloads/" in "/" + r[1]]
                    if dl and len({r[3] for r in dl}) == 1:
                        hit, rule = dl, f"{rl}-downloads/{pool_name}"
                        break
            if hit:
                break
        if not hit:
            rec.update(status="UNMATCHED")
            results.append(rec)
            continue
        repo, path, size, sha = hit[0]
        dest = DEST / f"{repo}__{Path(path).name}"
        if not (dest.exists() and dest.stat().st_size == int(size)):
            if int(size) > 60_000_000:
                rec.update(status="TOO_LARGE", repo=repo, path=path, bytes=int(size))
                results.append(rec)
                continue
            data = SS._api(f"https://api.github.com/repos/{SS.OWNER}/{repo}/git/blobs/{sha}",
                           "application/vnd.github.raw")
            if hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() != sha:
                rec.update(status="SHA_MISMATCH", repo=repo, path=path)
                results.append(rec)
                continue
            dest.write_bytes(data)
        rec.update(status="MATCHED", rule=rule, repo=repo, path=path, git_blob=sha, bytes=int(size),
                   local=str(dest.relative_to(ROOT)),
                   url=f"https://github.com/{SS.OWNER}/{repo}/blob/HEAD/{path}")
        results.append(rec)
        print(f"{rec['status']:9s} {rule:22s} {site:10s} {name[:60]}")
    for r in results:
        if r["status"] != "MATCHED":
            print(f"{r['status']:9s} {'':22s} {r['site']:10s} {r['name'][:60]}")
    OUT.write_text(json.dumps(results, indent=1) + "\n")
    print(f"matched {sum(r['status']=='MATCHED' for r in results)}/{len(results)} -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
