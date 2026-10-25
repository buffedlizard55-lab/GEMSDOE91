"""The S16-PC91 verifier must fail closed when pins are absent and never approve a slot."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_s16pc", ROOT / "scripts/verify_s16pc.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_raster(path: Path, values: np.ndarray) -> None:
    transform = Affine(100, 0, 243350, 0, -100, 4508550)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=None,
    ) as destination:
        destination.write(values.astype(np.float32), 1)


def prepare_fixture(root: Path, *, include_data: bool = True, candidate_value: float = 1.0, outside_value: float | None = None) -> Path:
    downloads = root / "docs/downloads"
    downloads.mkdir(parents=True)
    (root / "evidence").mkdir(parents=True)
    (root / "registry").mkdir(parents=True)
    name = "s16pc-verifier-fixture"
    shape = (8, 8)
    sample = root / "data/official/sample_submission.tif"
    catalogue = root / "data/official/existing_faults.tif"
    if include_data:
        sample.parent.mkdir(parents=True)
        footprint_ref = np.ones(shape, np.float32)
        footprint_ref[0, 7] = np.nan
        write_raster(sample, footprint_ref)
        cat = np.zeros(shape, np.float32)
        cat[0, 0] = 1.0
        write_raster(catalogue, cat)
    paths = {
        "sample_submission": "official/sample_submission.tif",
        "existing_faults": "official/existing_faults.tif",
    }
    files = []
    for key, rel in paths.items():
        p = root / "data" / rel
        if include_data:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            byte_count = p.stat().st_size
        else:
            digest = "0" * 64
            byte_count = 1
        files.append({
            "id": key,
            "local_subpath": rel,
            "sha256": digest,
            "bytes": byte_count,
        })
    (root / "registry/data_manifest.json").write_text(json.dumps({"files": files}))

    pred = np.zeros(shape, np.float32)
    pred[7, 7] = candidate_value
    if outside_value is not None:
        pred[0, 7] = outside_value
    tif = downloads / f"{name}-zeros.tif"
    write_raster(tif, pred)
    with zipfile.ZipFile(downloads / f"{name}-zeros.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(tif, arcname=tif.name)
    card = {
        "submission_name": name,
        "raster_sha256": hashlib.sha256(tif.read_bytes()).hexdigest(),
        "verdict": "negative",
        "ok_to_submit": False,
    }
    (root / "docs/run-card-S16PC.json").write_text(json.dumps(card))
    return root


def test_valid_format_verification_never_approves_submission(tmp_path, capsys):
    root = prepare_fixture(tmp_path)
    verifier = load_verifier()

    assert verifier.main(root) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PASS"
    assert report["format_pass"] is True
    assert report["ok_to_download"] is True
    assert report["ok_to_submit"] is False
    assert report["submission_ready"] is False
    assert report["checks"]["values_in_0_1"] is True
    assert report["checks"]["zero_outside_footprint"] is True
    assert report["checks"]["crs_match"] is True
    assert report["checks"]["transform_match"] is True
    assert json.loads((root / "evidence/s16pc_independent_check.json").read_text()) == report


def test_missing_pinned_data_is_structured_blocked_not_a_traceback(tmp_path, capsys):
    root = prepare_fixture(tmp_path, include_data=False)
    verifier = load_verifier()

    assert verifier.main(root) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "BLOCKED"
    assert "missing pinned sample_submission" in report["error"]
    assert report["ok_to_submit"] is False
    assert report["submission_ready"] is False
    saved = json.loads((root / "evidence/s16pc_independent_check.json").read_text())
    assert saved == report


def test_out_of_range_candidate_fails_without_becoming_submit_ready(tmp_path, capsys):
    root = prepare_fixture(tmp_path, candidate_value=1.5)
    verifier = load_verifier()

    assert verifier.main(root) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "FAIL"
    assert report["checks"]["values_in_0_1"] is False
    assert report["format_pass"] is False
    assert report["ok_to_download"] is False
    assert report["ok_to_submit"] is False
    assert report["submission_ready"] is False


def test_nonzero_outside_template_footprint_fails_closed(tmp_path, capsys):
    root = prepare_fixture(tmp_path, outside_value=1.0)
    verifier = load_verifier()

    assert verifier.main(root) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "FAIL"
    assert report["checks"]["zero_outside_footprint"] is False
    assert report["ok_to_download"] is False
    assert report["ok_to_submit"] is False
