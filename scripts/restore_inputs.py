#!/usr/bin/env python3
"""Deterministically restore and SHA-256-verify pinned inputs from registry/data_manifest.json.

Hard constraints (Agent Brief v2 §4.1–§4.3):
- Never contacts dropbox.com or drivendata.org.
- Never reads, stores, or transmits credentials.
- Verifies SHA-256 and exact byte length on every single file before and after copy.
- Supports ``--validation`` (11 lightweight core lineage + template + SGMC pins, ~12 MB)
  and full mode (all 14 pins including 19-band training_features.tif).
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_manifest.json"
FORBIDDEN_HOSTS = ("dropbox.com", "drivendata.org")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_allowed_url(url: str) -> None:
    low = url.lower()
    for host in FORBIDDEN_HOSTS:
        if host in low:
            raise RuntimeError(f"Forbidden host in restore URL: {url}")


def sparse_checkout_group(repo: str, ref: str, rel_paths: list[str], tmp_dir: Path) -> Path:
    repo_url = f"https://github.com/{repo}.git"
    check_allowed_url(repo_url)
    checkout = tmp_dir / "mirror"
    subprocess.run(
        ["git", "clone", "--quiet", "--depth=1", "--filter=blob:none", "--sparse", repo_url, str(checkout)],
        check=True,
    )
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if head != ref:
        subprocess.run(["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "origin", ref], check=True)
        subprocess.run(["git", "-C", str(checkout), "checkout", "--quiet", "--detach", ref], check=True)
    subprocess.run(
        ["git", "-C", str(checkout), "sparse-checkout", "set", "--no-cone", *("/" + p for p in rel_paths)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return checkout


def verify_entry(entry: dict) -> bool:
    p = ROOT / entry["local_path"]
    if not p.is_file():
        return False
    return p.stat().st_size == entry["bytes"] and sha256_file(p) == entry["sha256"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", action="store_true", help="Restore only tier='validation' pins (~12 MB).")
    parser.add_argument("--verify-only", action="store_true", help="Verify already-restored pins offline.")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [
        e for e in manifest["files"]
        if (e.get("tier") == "validation" if args.validation else True)
    ]

    if args.verify_only:
        for e in entries:
            if not verify_entry(e):
                raise RuntimeError(f"PIN VERIFICATION FAILED: {e['id']} ({e['local_path']})")
            print(f"PIN OK  {e['id']:28s} {e['sha256']} ({e['bytes']} B)")
        return 0

    (ROOT / "data").mkdir(exist_ok=True)

    # Group single-file entries by (repo, ref)
    groups: dict[tuple[str, str], list[dict]] = {}
    multipart_entries: list[dict] = []
    for e in entries:
        if e.get("multipart"):
            multipart_entries.append(e)
        else:
            groups.setdefault((e["repo"], e["ref"]), []).append(e)

    for (repo, ref), items in groups.items():
        pending = [e for e in items if not verify_entry(e)]
        if not pending:
            for e in items:
                print(f"PIN OK  {e['id']:28s} {e['sha256']}")
            continue
        for e in pending:
            dst = ROOT / e["local_path"]
            if dst.exists():
                raise RuntimeError(f"Refusing to overwrite corrupted file at {dst}")
        with tempfile.TemporaryDirectory(prefix="restore-", dir=ROOT / "data") as td:
            co = sparse_checkout_group(repo, ref, [e["path"] for e in pending], Path(td))
            for e in pending:
                src = co / e["path"]
                got_sha = sha256_file(src)
                got_bytes = src.stat().st_size
                if got_sha != e["sha256"] or got_bytes != e["bytes"]:
                    raise RuntimeError(f"Mirror mismatch on {e['id']}: {got_sha} ({got_bytes} B)")
                dst = ROOT / e["local_path"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                if not verify_entry(e):
                    dst.unlink(missing_ok=True)
                    raise RuntimeError(f"Post-copy verification failed on {e['id']}")
                print(f"RESTORED {e['id']:27s} {e['sha256']} ({got_bytes} B)")

    for e in multipart_entries:
        if verify_entry(e):
            print(f"PIN OK  {e['id']:28s} {e['sha256']}")
            continue
        dst = ROOT / e["local_path"]
        if dst.exists():
            raise RuntimeError(f"Refusing to overwrite corrupted multipart target at {dst}")
        parts: list[str] = e["parts"]
        with tempfile.TemporaryDirectory(prefix="restore-mp-", dir=ROOT / "data") as td:
            co = sparse_checkout_group(e["repo"], e["ref"], parts, Path(td))
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp_target = dst.with_suffix(".tif.partial")
            with tmp_target.open("wb") as out:
                for part in parts:
                    with (co / part).open("rb") as inp:
                        shutil.copyfileobj(inp, out, 4 << 20)
            tmp_target.replace(dst)
        if not verify_entry(e):
            dst.unlink(missing_ok=True)
            raise RuntimeError(f"Post-reassembly SHA/byte mismatch on {e['id']}")
        print(f"RESTORED {e['id']:27s} {e['sha256']} ({e['bytes']} B)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
