"""Pinned input manifest handling: fetch + sha256 verify, never memory.

Every input a build touches must appear in registry/data_manifest.json with a
sha256 and byte length. `fetch` writes into data/ (gitignored) and refuses to
leave a file whose hash does not match the pin.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

MANIFEST = Path("registry/data_manifest.json")


def load_manifest(path: str | Path = MANIFEST) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_entry(entry: dict, local_path: Path) -> tuple[bool, str]:
    if not local_path.exists():
        return False, f"MISSING {local_path}"
    got_len = local_path.stat().st_size
    if got_len != entry["bytes"]:
        return False, f"BYTES {local_path} {got_len} != {entry['bytes']}"
    got = sha256_file(local_path)
    if got != entry["sha256"]:
        return False, f"SHA256 {local_path} {got[:16]}.. != {entry['sha256'][:16]}.."
    return True, f"OK {entry['id']}"


def local_path_for(entry: dict, data_root: Path) -> Path:
    return data_root / entry["local_subpath"]


def mirror_url(mirror: str) -> str:
    """'OWNER/REPO:path' -> api.github.com raw contents URL.

    api.github.com is used because raw.githubusercontent.com is not reachable
    from this sandbox (allowed hosts: github.com, codeload, api.github.com).
    """
    repo, _, path = mirror.partition(":")
    owner, _, name = repo.partition("/")
    return f"https://api.github.com/repos/{owner}/{name}/contents/{path}"


def _auth_header() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        try:
            token = subprocess.run(["gh", "auth", "token"], capture_output=True,
                                   text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            token = ""
    headers = {"Accept": "application/vnd.github.raw"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch(entry: dict, data_root: Path) -> tuple[bool, str]:
    """Download a pinned entry from its public mirror and verify the pin."""
    dest = local_path_for(entry, data_root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return verify_entry(entry, dest)
    mirror = entry.get("public_mirror")
    if not mirror:
        return False, f"NO MIRROR for {entry['id']} (human machine only)"
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(mirror_url(mirror), headers=_auth_header())
    with urllib.request.urlopen(req, timeout=180) as resp, open(tmp, "wb") as fh:
        fh.write(resp.read())
    ok, msg = verify_entry(entry, tmp)
    if not ok:
        tmp.unlink(missing_ok=True)
        return False, msg
    tmp.replace(dest)
    return True, msg


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verify or fetch pinned inputs.")
    ap.add_argument("action", choices=["check", "fetch"])
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--only", default=None, help="comma-separated ids")
    args = ap.parse_args(argv[1:])

    man = load_manifest()
    wanted = set(args.only.split(",")) if args.only else None
    root = Path(args.data_root)
    bad = 0
    for entry in man["files"]:
        if wanted and entry["id"] not in wanted:
            continue
        if args.action == "fetch":
            ok, msg = fetch(entry, root)
        else:
            ok, msg = verify_entry(entry, local_path_for(entry, root))
        if not ok:
            bad += 1
        print(("OK   " if ok else "FAIL ") + msg)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
