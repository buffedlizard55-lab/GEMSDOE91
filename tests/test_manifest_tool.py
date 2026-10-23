"""The release manifest is the only contract that a rebuild reproduced the same bytes.

`releases/*.tif` are gitignored, so these tests are what stops the manifest drifting from
what is on disk and from what the ledger says about each file. They are cheap and need
only the manifest plus the ledger; the byte check runs when the files are present.
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "releases" / "MANIFEST.json"
LEDGER = ROOT / "ledger" / "submissions.csv"


def load_manifest() -> dict:
    assert MANIFEST.is_file(), "releases/MANIFEST.json is missing"
    return json.loads(MANIFEST.read_text())


def ledger_rows() -> list[dict]:
    with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def test_manifest_entries_are_complete_and_unique():
    files = load_manifest()["files"]
    assert files, "manifest lists no releases"
    names = [f["file"] for f in files]
    assert len(names) == len(set(names)), "duplicate entry in the manifest"
    shas = [f["sha256"] for f in files]
    assert len(shas) == len(set(shas)), "two releases share a sha256"
    for f in files:
        assert set(f) >= {"file", "sha256", "bytes", "axis", "n_dots"}, f["file"]
        assert len(f["sha256"]) == 64, f["file"]
        assert f["axis"] in {"PRUNE", "SPACING", "RELIEF"}, f["file"]
        # a release is either the parent's dot count (count-preserving) or fewer (delete-only)
        assert isinstance(f["n_dots"], int) and 0 < f["n_dots"] <= 37_654, f["file"]


def test_every_manifest_hash_is_a_ledger_row():
    """A release must be registered before it can be shipped."""
    known = set()
    for row in ledger_rows():
        for key in ("sha256", "sha256_zeros"):
            if row.get(key, "").strip():
                known.add(row[key].strip())
    for f in load_manifest()["files"]:
        assert f["sha256"] in known, f"{f['file']} is not in the ledger"


def test_manifest_matches_disk_when_the_files_are_built():
    files = load_manifest()["files"]
    built = sorted(p for p in (ROOT / "releases").glob("*.tif"))
    if not built:
        pytest.skip("releases/*.tif are not built here (they are gitignored)")
    on_disk = {p.name for p in built}
    listed = {f["file"] for f in files}
    assert on_disk == listed, (
        f"on disk but not in the manifest: {sorted(on_disk - listed)}; "
        f"in the manifest but not built: {sorted(listed - on_disk)}")
    for f in files:
        p = ROOT / "releases" / f["file"]
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        assert h.hexdigest() == f["sha256"], f"{f['file']}: bytes changed"
        assert p.stat().st_size == f["bytes"], f"{f['file']}: size changed"


def test_check_mode_agrees_with_the_tests():
    built = list((ROOT / "releases").glob("*.tif"))
    if not built:
        pytest.skip("nothing built here")
    out = subprocess.run([sys.executable, "scripts/update_release_manifest.py", "--check"],
                         cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "0 problem(s)" in out.stdout
