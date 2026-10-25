#!/usr/bin/env python3
"""Render the historical GEO91 research download, never promote it.

Identity checks concern the file actually linked on the front door, not a
previous run. Full pinned-reference format checks run in audit_downloads.py.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def current_download(root=ROOT):
    docs = root / "docs"
    card = json.loads((docs / "run-card-GEO91.json").read_text())
    if card.get("submission_ready") is not False or card.get("verdict") != "negative":
        raise ValueError("Historical portal requires an explicitly negative research card")
    tif = (root / card["e2_raster_path"]).resolve()
    if not tif.is_relative_to((docs / "downloads").resolve()) or tif.suffix != ".tif":
        raise ValueError("Current TIFF must be inside docs/downloads")
    zipped = tif.with_suffix(".zip")
    policy = json.loads((root / "registry/artifact_policy.json").read_text())["files"]
    indexed = {row["path"]: row for row in policy}
    if len(indexed) != len(policy):
        raise ValueError("Duplicate artifact policy path")
    hashes = {}
    for path in (tif, zipped):
        key = path.relative_to(root.resolve()).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if key not in indexed or digest != indexed[key]["sha256"]:
            raise ValueError("Current download does not match registered bytes")
        hashes[path.suffix] = digest
    if hashes[".tif"] != card["e2_raster_sha256"]:
        raise ValueError("Current download does not match run card")
    with zipfile.ZipFile(zipped) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != tif.name or members[0].file_size != tif.stat().st_size:
            raise ValueError("Current ZIP must contain exactly the advertised TIFF")
        if archive.read(tif.name) != tif.read_bytes():
            raise ValueError("Current ZIP member differs from TIFF")
    return {
        "run_card": "run-card-GEO91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Historical research download; byte identity is not science or uniqueness approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to(docs.resolve()).as_posix(),
        "zip": zipped.relative_to(docs.resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
    }


def render() -> None:
    docs = ROOT / "docs"
    current = current_download(ROOT)  # fail before replacing any published page
    idx_bytes = (docs / "geo91-index-src.html").read_bytes()
    exe_bytes = (docs / "geo91-exec-src.html").read_bytes()
    (docs / "index.html").write_bytes(idx_bytes)
    (docs / "executive-summary.html").write_bytes(exe_bytes)
    (docs / "geo91.html").write_bytes(idx_bytes)
    (docs / "geo91-executive-summary.html").write_bytes(exe_bytes)
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
