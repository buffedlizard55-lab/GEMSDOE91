"""Fail-closed GeoTIFF packaging for a potential GEMS submission.

The writer never clips, fills, or otherwise repairs model output.  It validates
in memory, writes to private temporary paths, validates the on-disk TIFF and ZIP,
and only then publishes them with no-clobber links, rolling back on ordinary
exceptions. A hard crash is not an atomic multi-file transaction. Local format
validity is not a uniqueness clearance or organizer acceptance.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path

import numpy as np

from . import gates, grid
from .validate import assert_submittable, validate


def _temp_path(parent: Path, stem: str, suffix: str) -> Path:
    fd, name = tempfile.mkstemp(prefix=f".{stem}.", suffix=suffix, dir=parent)
    os.close(fd)
    return Path(name)


def write_submission(path, prediction, sample, footprint, *, note, name,
                     catalogue=None, metadata=None):
    """Write a locally validated single-band GeoTIFF and one-TIFF ZIP.

    ``name`` and ``note`` are limited to 140 characters.  The prediction must
    already be a 2-D finite float field in ``[0,1]``, aligned with the footprint,
    and have no positive support outside it.  If ``catalogue`` is supplied, the
    candidate must also have zero positive pixels on mapped faults.
    """
    if not isinstance(name, str) or not name.strip() or len(name) > 140:
        raise ValueError('name must contain 1..140 non-whitespace characters')
    if not isinstance(note, str) or not note.strip() or len(note) > 140:
        raise ValueError('note must contain 1..140 non-whitespace characters')

    for label, value in (('prediction', prediction), ('footprint', footprint), ('catalogue', catalogue)):
        if value is not None and np.ma.isMaskedArray(value) and np.ma.getmaskarray(value).any():
            raise ValueError(f'{label} has masked values; resolve them explicitly')
    p = np.asarray(prediction)
    raw_fp = np.asarray(footprint)
    if p.ndim != 2 or p.shape != raw_fp.shape:
        raise ValueError('prediction and footprint must be matching 2-D arrays')
    if (raw_fp.dtype.kind not in 'buif' or not np.isfinite(raw_fp).all()
            or not np.isin(raw_fp, [0, 1]).all() or not raw_fp.any()):
        raise ValueError('footprint must be a nonempty finite binary mask')
    fp = raw_fp.astype(bool, copy=False)
    if p.dtype.kind not in 'buif':
        raise ValueError('prediction must be real and numeric')
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('prediction must already be normalized, finite and in [0,1]; no silent repair')
    if np.any((p > 0) & ~fp):
        raise ValueError('positive prediction mass outside the valid footprint')
    cat = None
    if catalogue is not None:
        raw_cat = np.asarray(catalogue)
        if raw_cat.shape != p.shape:
            raise ValueError('catalogue shape must match the prediction grid')
        if (raw_cat.dtype.kind not in 'buif' or not np.isfinite(raw_cat[fp]).all()
                or not np.isin(raw_cat[fp], [0, 1]).all()):
            raise ValueError('catalogue must be a finite binary mask inside the footprint')
        cat = (raw_cat > 0) & fp
        if np.any((p > 0) & cat):
            raise ValueError('positive prediction mass on the mapped catalogue')

    path = Path(path)
    if path.suffix.lower() not in {'.tif', '.tiff'}:
        raise ValueError('submission path must end in .tif or .tiff')
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = Path(sample)
    if not sample.is_file():
        raise FileNotFoundError(f'sample grid does not exist: {sample}')

    zip_path = path.with_suffix('.zip')
    receipt_path = path.with_suffix('.json')
    existing = [candidate for candidate in (path, zip_path, receipt_path) if candidate.exists()]
    if existing:
        raise FileExistsError(f'refusing to overwrite existing submission outputs: {existing}')
    tmp_tif = tmp_zip = tmp_receipt = None
    committed = []
    try:
        tmp_tif = _temp_path(path.parent, path.stem, path.suffix)
        tmp_zip = _temp_path(path.parent, path.stem, '.zip')
        tmp_receipt = _temp_path(path.parent, path.stem, '.json')
        # grid.write_geotiff itself rejects shape, dtype, NaN/inf, and range drift.
        grid.write_geotiff(tmp_tif, p.astype(np.float32, copy=False), nodata=None)
        report = gates.format_report(tmp_tif, sample, footprint=fp)
        if not report['ok']:
            raise ValueError(f'on-disk template validator rejected output: {report["problems"]}')
        local_validation = validate(tmp_tif, fp, cat)
        try:
            assert_submittable(local_validation)
        except AssertionError as exc:
            raise ValueError(f'on-disk range/format validator rejected output: {exc}') from exc
        if report.get('n_nonzero', 0) != int((p > 0).sum()):
            raise ValueError('on-disk positive support changed during serialization')
        local_validation['file'] = str(path)
        report['path'] = str(path)

        # A submission ZIP contains ONLY the one TIFF; evidence stays adjacent.
        with zipfile.ZipFile(tmp_zip, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            info = zipfile.ZipInfo(path.name, date_time=(2026, 10, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, tmp_tif.read_bytes())
        with zipfile.ZipFile(tmp_zip) as z:
            if z.namelist() != [path.name] or z.read(path.name) != tmp_tif.read_bytes():
                raise IOError('single-TIFF ZIP roundtrip failed')

        receipt = dict(
            file=path.name,
            sha256=report['sha256'],
            bytes=tmp_tif.stat().st_size,
            submission_name=name,
            note=note,
            note_chars=len(note),
            validator=local_validation,
            template_report=report,
            zip_file=zip_path.name,
            zip_sha256=hashlib.sha256(tmp_zip.read_bytes()).hexdigest(),
            approved_for_weekly_slot=False,
            promoted=False,
            submission_slots_used=0,
            status='locally validated within separately recorded inventory scope; not organizer acceptance or slot approval',
            metadata=metadata or {},
        )
        tmp_receipt.write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n', encoding='utf-8')

        # Stage auxiliary files first and commit the TIFF last as the primary artifact.
        for source, destination in ((tmp_zip, zip_path), (tmp_receipt, receipt_path), (tmp_tif, path)):
            # An exists() check alone races with concurrent writers. Hard-link
            # each file on the same filesystem so an existing destination can
            # never be replaced; rollback removes only links created here.
            os.link(source, destination)
            committed.append((source, destination))
        return receipt
    except Exception:
        # Do not knowingly delete a destination replaced by a competing writer.
        for source, destination in reversed(committed):
            try:
                if os.path.samefile(source, destination):
                    destination.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        for temporary in (tmp_tif, tmp_zip, tmp_receipt):
            if temporary is None:
                continue
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
