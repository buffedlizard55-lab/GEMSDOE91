#!/usr/bin/env python3
"""Render the current research download and keep the historical GEO91 check.

The front door is the newest registered research file. current_download()
still validates the historical GEO91 bytes so an older card cannot silently
replace that file. Neither path can set ok_to_submit true.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def _registered_pair(root, tif_rel, expected_sha):
    docs = root / "docs"
    tif = (root / tif_rel).resolve()
    if not tif.is_relative_to((docs / "downloads").resolve()) or tif.suffix != ".tif":
        raise ValueError("TIFF must be inside docs/downloads")
    zipped = tif.with_suffix(".zip").resolve()
    if not zipped.is_relative_to((docs / "downloads").resolve()) or zipped.suffix != ".zip":
        raise ValueError("ZIP must be inside docs/downloads")
    policy = json.loads((root / "registry/artifact_policy.json").read_text())["files"]
    indexed = {row["path"]: row for row in policy}
    if len(indexed) != len(policy):
        raise ValueError("Duplicate artifact policy path")
    hashes = {}
    for path in (tif, zipped):
        key = path.relative_to(root.resolve()).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if key not in indexed or digest != indexed[key]["sha256"]:
            raise ValueError("Download does not match registered bytes")
        hashes[path.suffix] = digest
    if hashes[".tif"] != expected_sha:
        raise ValueError("Download does not match run card")
    with zipfile.ZipFile(zipped) as archive:
        members = archive.infolist()
        if len(members) != 1 or members[0].filename != tif.name or members[0].file_size != tif.stat().st_size:
            raise ValueError("ZIP must contain exactly the advertised TIFF")
        if archive.read(tif.name) != tif.read_bytes():
            raise ValueError("ZIP member differs from TIFF")
    return tif, zipped, hashes


def current_download(root=ROOT):
    """Historical GEO91 byte check. Tests mutate this card and expect ValueError."""
    docs = root / "docs"
    card = json.loads((docs / "run-card-GEO91.json").read_text())
    if card.get("submission_ready") is not False or card.get("verdict") != "negative":
        raise ValueError("Historical portal requires an explicitly negative research card")
    tif, zipped, hashes = _registered_pair(root, card["e2_raster_path"], card["e2_raster_sha256"])
    return {
        "run_card": "run-card-GEO91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Historical research download; byte identity is not science or uniqueness approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to((root / "docs").resolve()).as_posix(),
        "zip": zipped.relative_to((root / "docs").resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
    }


def front_door(root=ROOT):
    docs = root / "docs"
    card = json.loads((docs / "run-card-XG91.json").read_text())
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("Front door requires an explicitly negative research card")
    tif, zipped, hashes = _registered_pair(root, card["raster_path"], card["raster_sha256"])
    return {
        "run_card": "run-card-XG91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Current research download; format pass is not submission approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to(docs.resolve()).as_posix(),
        "zip": zipped.relative_to(docs.resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
        "verdict": "negative",
        "note": "Renderer never sets ok_to_submit true.",
    }


def render() -> None:
    docs = ROOT / "docs"
    current_download(ROOT)  # fail before replacing any published page
    current = front_door(ROOT)
    idx_bytes = (docs / "geo91-index-src.html").read_bytes()
    exe_bytes = (docs / "geo91-exec-src.html").read_bytes()
    (docs / "index.html").write_bytes(idx_bytes)
    (docs / "executive-summary.html").write_bytes(exe_bytes)
    # geo91.html stays the historical GEO91 page. Do not overwrite it.
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
