"""Independent delivery checks; fixtures are not competition submissions."""
import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin

from scripts.audit_downloads import inspect_raster


def encoded(values, *, count=1, transform=None, nodata=None, dtype='float32'):
    transform = transform or from_origin(250000, 4500000, 100, 100)
    with MemoryFile() as mem:
        with mem.open(driver='GTiff', height=3, width=4, count=count,
                      dtype=dtype, crs='EPSG:32611', transform=transform,
                      nodata=nodata) as dst:
            for band in range(1, count + 1):
                dst.write(values, band)
        return mem.read()


def inspect(data):
    reference = (1, (3, 4), rasterio.crs.CRS.from_epsg(32611),
                 from_origin(250000, 4500000, 100, 100))
    footprint = np.ones((3, 4), dtype=bool)
    footprint[0, 0] = False
    catalogue = np.zeros((3, 4), dtype=bool)
    catalogue[1, 1] = True
    return inspect_raster(data, reference, footprint, catalogue)


def test_valid_format_is_not_submission_permission():
    result = inspect(encoded(np.zeros((3, 4), dtype='float32')))
    assert result['status'] == 'PASS'
    assert result['ok_to_submit'] is False


@pytest.mark.parametrize('value', [np.nan, np.inf, -1, 1.01])
def test_bad_values_cannot_hide_behind_nodata(value):
    values = np.zeros((3, 4), dtype='float32')
    values[2, 2] = value
    result = inspect(encoded(values))
    assert result['status'] == 'FAIL'
    assert result['checks']['values_in_0_1'] is False


@pytest.mark.parametrize('cell,check', [((0, 0), 'zero_outside_footprint'),
                                      ((1, 1), 'visible_catalogue_masked')])
def test_masks(cell, check):
    values = np.zeros((3, 4), dtype='float32')
    values[cell] = 1
    result = inspect(encoded(values))
    assert result['checks'][check] is False
    assert result['status'] == 'FAIL'


@pytest.mark.parametrize('kwargs', [dict(count=2), dict(nodata=-9999),
                                   dict(transform=from_origin(250001, 4500000, 100, 100))])
def test_grid_band_and_nodata(kwargs):
    assert inspect(encoded(np.zeros((3, 4), dtype='float32'), **kwargs))['status'] == 'FAIL'


def repository(tmp_path):
    import hashlib
    import json
    from scripts.audit_downloads import audit
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'data').mkdir()
    (tmp_path / 'docs/downloads').mkdir(parents=True)
    data = encoded(np.zeros((3, 4), dtype='float32'))
    rows = []
    for name in ('sample_submission', 'existing_faults'):
        (tmp_path / 'data' / (name + '.tif')).write_bytes(data)
        rows.append(dict(id=name, local_subpath=name + '.tif', sha256=hashlib.sha256(data).hexdigest()))
    (tmp_path / 'registry/data_manifest.json').write_text(json.dumps(dict(files=rows)))
    path = 'docs/downloads/research.tif'
    (tmp_path / path).write_bytes(data)
    policy = [dict(path=path, sha256=hashlib.sha256(data).hexdigest(), status='current_research_only')]
    (tmp_path / 'registry/artifact_policy.json').write_text(json.dumps(dict(files=policy)))
    return audit, policy


def test_inventory_is_complete_and_pins_are_required(tmp_path):
    audit, _ = repository(tmp_path)
    assert audit(tmp_path)['format_pass'] == 1
    (tmp_path / 'docs/downloads/unregistered.tif').write_bytes(b'not a TIFF')
    with pytest.raises(ValueError, match='Incomplete inventory'):
        audit(tmp_path)
    (tmp_path / 'docs/downloads/unregistered.tif').unlink()
    (tmp_path / 'data/sample_submission.tif').write_bytes(b'wrong reference')
    with pytest.raises(ValueError, match='Untrusted reference'):
        audit(tmp_path)


@pytest.mark.parametrize('member,payload,passed', [('research.tif', None, True),
    ('research.tif', b'wrong bytes', False), ('../research.tif', None, False),
    ('empty.zip', b'', False)])
def test_zip_member_identity_and_flat_layout(tmp_path, member, payload, passed):
    import hashlib
    import json
    import zipfile
    audit, policy = repository(tmp_path)
    path = tmp_path / 'docs/downloads/research.zip'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr(member, payload if payload is not None else
                         (tmp_path / 'docs/downloads/research.tif').read_bytes())
    policy.append(dict(path='docs/downloads/research.zip', sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       status='current_research_only'))
    (tmp_path / 'registry/artifact_policy.json').write_text(json.dumps(dict(files=policy)))
    report = audit(tmp_path)
    assert report['files'][1]['status'] == ('PASS' if passed else 'FAIL')
    assert report['ok_to_submit'] is False


@pytest.mark.parametrize('dtype', ['uint8', 'float64'])
def test_non_float32_is_not_format_certified(dtype):
    report = inspect(encoded(np.zeros((3, 4), dtype=dtype), dtype=dtype))
    assert report['status'] == 'FAIL'
    assert report['checks']['float32'] is False
    assert report['ok_to_submit'] is False


def test_inventory_rejects_masked_or_nonbinary_catalogue(tmp_path):
    import hashlib
    import json
    audit, _ = repository(tmp_path)
    catalogue = tmp_path / 'data/existing_faults.tif'
    invalid = np.zeros((3, 4), dtype='float32'); invalid[1, 1] = 2
    catalogue.write_bytes(encoded(invalid))
    manifest_path = tmp_path / 'registry/data_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    next(row for row in manifest['files'] if row['id'] == 'existing_faults')['sha256'] = hashlib.sha256(catalogue.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='nonfinite, nonbinary or masked'):
        audit(tmp_path)
    catalogue.write_bytes(encoded(np.zeros((3, 4), dtype='float32'), nodata=0))
    next(row for row in manifest['files'] if row['id'] == 'existing_faults')['sha256'] = hashlib.sha256(catalogue.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='nonfinite, nonbinary or masked'):
        audit(tmp_path)
