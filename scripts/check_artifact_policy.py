#!/usr/bin/env python3
"""Reject tracked raw rasters; allow only explicitly pinned prediction artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    policy = json.loads((ROOT / 'registry/artifact_policy.json').read_text())
    allowed = {r['path']: r for r in policy['files']}
    tracked = subprocess.check_output(['git','ls-files','-z','--cached','--others','--exclude-standard'],cwd=ROOT).decode().split('\0')
    artifacts = sorted({p for p in tracked if p.lower().endswith(('.tif','.tiff','.zip'))})
    for name in artifacts:
        if not name.startswith('docs/downloads/') or name not in allowed:
            raise ValueError(f'Unregistered or raw raster/archive must not be tracked: {name}')
        row = allowed[name]
        actual = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if actual != row['sha256']:
            raise ValueError(f'Published artifact drift: {name}')
        if row['status'] not in ('legacy_quarantined','parallel_quarantined','current_research_only','selector_approved'):
            raise ValueError(f'Unknown artifact status: {row["status"]}')
    if set(allowed) != set(artifacts):
        raise ValueError(f'Artifact-policy/files mismatch: {set(allowed)^set(artifacts)}')
    print(f'PASS: {len(artifacts)} explicitly registered prediction artifacts; no raw raster/archive tracked.')


if __name__ == '__main__': main()
