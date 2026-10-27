import hashlib
import json
from pathlib import Path
import pytest
from scripts.source_integrity import verify_historical_source


def test_corrected_and_historical_sources_are_both_pinned(tmp_path):
    root = tmp_path
    current = root / 'src/gems91/novelty.py'
    archived = root / 'evidence/s22/novelty-source-20261026.py.txt'
    manifest = root / 'docs/review-8e8d86f2/source-correction.json'
    for p in (current, archived, manifest): p.parent.mkdir(parents=True, exist_ok=True)
    current.write_bytes(b'corrected')
    archived.write_bytes(b'original')
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    entry = {'corrected_source': 'src/gems91/novelty.py', 'current_sha256': sha(current),
             'historical_source_archive': 'evidence/s22/novelty-source-20261026.py.txt',
             'historical_sha256': sha(archived)}
    manifest.write_text(json.dumps({'novelty_gate': entry}))
    verify_historical_source(root, entry['corrected_source'], entry['historical_sha256'])
    current.write_bytes(b'tampered corrected')
    with pytest.raises(ValueError, match='corrected source drift'):
        verify_historical_source(root, entry['corrected_source'], entry['historical_sha256'])
    current.write_bytes(b'corrected')
    archived.write_bytes(b'tampered original')
    with pytest.raises(ValueError, match='historical source|Historical source'):
        verify_historical_source(root, entry['corrected_source'], entry['historical_sha256'])
