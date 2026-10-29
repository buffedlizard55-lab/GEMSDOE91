"""Race safety and rollback for the shared template, using synthetic I/O only."""
import hashlib
from pathlib import Path

import numpy as np
import pytest
from vendor.gems57 import submission_writer as writer


def stub_packaging(monkeypatch):
    monkeypatch.setattr(writer.grid, 'write_geotiff',
                        lambda path, p, nodata: Path(path).write_bytes(b'synthetic geotiff'))
    def report(path, sample, footprint):
        return {'ok': True, 'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(), 'n_nonzero': 1}
    monkeypatch.setattr(writer.gates, 'format_report', report)
    monkeypatch.setattr(writer, 'validate', lambda *args: {'ok': True})
    monkeypatch.setattr(writer, 'assert_submittable', lambda result: None)


def test_competing_creation_after_check_is_never_overwritten(tmp_path, monkeypatch):
    stub_packaging(monkeypatch)
    sample = tmp_path / 'sample.tif'; sample.write_bytes(b'fixture')
    prediction = np.zeros((3, 3), np.float32); prediction[1, 1] = 1
    target = tmp_path / 'candidate.tif'
    real_link = writer.os.link
    def competing_link(source, destination):
        destination = Path(destination)
        if destination.name == 'candidate.json':
            destination.write_bytes(b'other writer owns this')
        real_link(source, destination)
    monkeypatch.setattr(writer.os, 'link', competing_link)
    with pytest.raises(FileExistsError):
        writer.write_submission(target, prediction, sample, np.ones((3, 3), bool),
                                note='Research fixture', name='fixture')
    assert not target.exists()
    assert not target.with_suffix('.zip').exists()  # rollback of our first link
    assert target.with_suffix('.json').read_bytes() == b'other writer owns this'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['candidate.json', 'sample.tif']


def test_successful_package_is_still_research_only(tmp_path, monkeypatch):
    stub_packaging(monkeypatch)
    sample = tmp_path / 'sample.tif'; sample.write_bytes(b'fixture')
    prediction = np.zeros((3, 3), np.float32); prediction[1, 1] = 1
    target = tmp_path / 'candidate.tif'
    receipt = writer.write_submission(target, prediction, sample, np.ones((3, 3), bool),
                                      note='Research fixture', name='fixture')
    assert receipt['promoted'] is False and receipt['approved_for_weekly_slot'] is False
    before = {p: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(FileExistsError):
        writer.write_submission(target, prediction, sample, np.ones((3, 3), bool),
                                note='Research fixture', name='fixture')
    assert {p: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_rollback_preserves_file_replaced_by_a_competing_writer(tmp_path, monkeypatch):
    stub_packaging(monkeypatch)
    sample = tmp_path / 'sample.tif'; sample.write_bytes(b'fixture')
    prediction = np.zeros((3, 3), np.float32); prediction[1, 1] = 1
    target = tmp_path / 'candidate.tif'
    real_link = writer.os.link
    count = 0
    def competing_replace(source, destination):
        nonlocal count
        count += 1
        if count == 2:
            first = target.with_suffix('.zip')
            first.unlink()
            first.write_bytes(b'other writer replacement')
            raise OSError('concurrent failure')
        real_link(source, destination)
    monkeypatch.setattr(writer.os, 'link', competing_replace)
    with pytest.raises(OSError, match='concurrent failure'):
        writer.write_submission(target, prediction, sample, np.ones((3, 3), bool),
                                note='Research fixture', name='fixture')
    assert target.with_suffix('.zip').read_bytes() == b'other writer replacement'
    assert not target.exists() and not target.with_suffix('.json').exists()


@pytest.mark.parametrize('problem', ['masked_prediction', 'complex_prediction', 'masked_footprint',
                                      'nan_footprint', 'fractional_footprint', 'empty_footprint',
                                      'masked_catalogue', 'nan_catalogue', 'fractional_catalogue'])
def test_shared_writer_rejects_ambiguous_inputs_before_writing(tmp_path, problem):
    sample = tmp_path / 'sample.tif'; sample.write_bytes(b'fixture')
    p = np.zeros((3, 3)); p[1, 1] = 1
    fp = np.ones((3, 3), bool)
    cat = np.zeros((3, 3), bool)
    if problem == 'masked_prediction': p = np.ma.array(p, mask=np.eye(3, dtype=bool))
    if problem == 'complex_prediction': p = p.astype(complex)
    if problem == 'masked_footprint': fp = np.ma.array(fp, mask=np.eye(3, dtype=bool))
    if problem == 'nan_footprint': fp = fp.astype(float); fp[0, 0] = np.nan
    if problem == 'fractional_footprint': fp = fp.astype(float); fp[0, 0] = .5
    if problem == 'empty_footprint': fp[:] = False
    if problem == 'masked_catalogue': cat = np.ma.array(cat, mask=np.eye(3, dtype=bool))
    if problem == 'nan_catalogue': cat = cat.astype(float); cat[0, 0] = np.nan
    if problem == 'fractional_catalogue': cat = cat.astype(float); cat[0, 0] = .5
    with pytest.raises(ValueError):
        writer.write_submission(tmp_path / 'invalid.tif', p, sample, fp,
                                catalogue=cat, note='Research fixture', name='fixture')
    assert sorted(path.name for path in tmp_path.iterdir()) == ['sample.tif']
