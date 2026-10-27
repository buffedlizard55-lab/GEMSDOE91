"""Verify a historical source hash and any explicitly archived correction.

Historical provenance files are immutable; correcting a shared gate must not
pretend a newly edited source was the one that produced an old result.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

CORRECTIONS = {
    'src/gems91/omtj22.py': (None, 'evidence/s22/omtj22-source-20261026.py.txt'),
    'src/gems91/novelty.py': ('novelty_gate', 'evidence/s22/novelty-source-20261026.py.txt'),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_historical_source(root: Path, name: str, historical_sha256: str) -> None:
    root = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Historical source path escapes repository: ' + name)
    if name not in CORRECTIONS:
        if digest(path) != historical_sha256:
            raise ValueError('Measured implementation drift: ' + name)
        return
    key, archive_name = CORRECTIONS[name]
    manifest = json.loads((root / 'docs/review-8e8d86f2/source-correction.json').read_text())
    entry = manifest if key is None else manifest.get(key, {})
    archive = (root / archive_name).resolve()
    if (not archive.is_relative_to(root)
            or entry.get('corrected_source') != name
            or entry.get('historical_sha256') != historical_sha256
            or entry.get('historical_source_archive') != archive_name
            or digest(archive) != historical_sha256
            or digest(path) != entry.get('current_sha256')):
        raise ValueError('Historical source or corrected source drift: ' + name)
