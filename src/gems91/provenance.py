"""Authenticate historical source bytes alongside explicitly pinned later fixes."""
from pathlib import Path
import hashlib
import json


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_recorded_source(root, name, recorded_sha256):
    """Check unchanged source or both the archived original and a pinned fix.

    The historical digest remains the one supplied by the run's own provenance;
    the correction manifest never substitutes a new digest for that record.
    """
    root = Path(root).resolve()
    source = (root / name).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError(f'Missing or unsafe implementation source: {name}')
    actual = _sha(source)
    if actual == recorded_sha256:
        return 'UNCHANGED'
    manifest = json.loads((root / 'docs/s22/source-integrity.json').read_text())
    correction = manifest.get('postrun_corrections', {}).get(name, {})
    archive = (root / correction.get('recorded_archive', '')).resolve()
    allowed = (root / 'docs/s22/recorded-source').resolve()
    if (not archive.is_relative_to(allowed) or not archive.is_file()
            or _sha(archive) != recorded_sha256
            or actual != correction.get('current_sha256')):
        raise ValueError(f'Measured implementation drift: {name}')
    return 'ARCHIVED_ORIGINAL_AND_PINNED_CORRECTION'
