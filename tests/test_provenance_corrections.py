import hashlib
import json
from pathlib import Path

import pytest
from src.gems91.provenance import verify_recorded_source


def digest(value):
    return hashlib.sha256(value).hexdigest()


def test_recorded_and_corrected_sources_must_both_match(tmp_path):
    source = tmp_path / 'src/old.py'
    source.parent.mkdir(parents=True)
    source.write_bytes(b'new fix')
    archive = tmp_path / 'docs/s22/recorded-source/old.py.txt'
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b'old source')
    manifest = tmp_path / 'docs/s22/source-integrity.json'
    manifest.write_text(json.dumps({'postrun_corrections': {
        'src/old.py': {'recorded_archive': 'docs/s22/recorded-source/old.py.txt',
                       'current_sha256': digest(b'new fix')}
    }}))
    assert verify_recorded_source(tmp_path, 'src/old.py', digest(b'old source')) == 'ARCHIVED_ORIGINAL_AND_PINNED_CORRECTION'
    source.write_bytes(b'unrecorded change')
    with pytest.raises(ValueError, match='drift'):
        verify_recorded_source(tmp_path, 'src/old.py', digest(b'old source'))
    source.write_bytes(b'new fix')
    archive.write_bytes(b'tampered')
    with pytest.raises(ValueError, match='drift'):
        verify_recorded_source(tmp_path, 'src/old.py', digest(b'old source'))


def test_unchanged_source_and_path_escape(tmp_path):
    source = tmp_path / 'file.py'
    source.write_bytes(b'original')
    assert verify_recorded_source(tmp_path, 'file.py', digest(b'original')) == 'UNCHANGED'
    with pytest.raises(ValueError, match='unsafe'):
        verify_recorded_source(tmp_path, '../file.py', digest(b'original'))
