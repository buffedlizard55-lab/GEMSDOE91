from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402


def _make_mini_template_and_cat(tmp_path: Path, h: int = 80, w: int = 80) -> tuple[Path, Path, np.ndarray, np.ndarray]:
    transform = from_origin(300000.0, 4500000.0, 100.0, 100.0)
    footprint = np.ones((h, w), dtype=bool)
    footprint[:4, :] = False
    footprint[:, :4] = False

    tpl_arr = np.where(footprint, np.float32(0.0), np.float32(np.nan))
    tpl_path = tmp_path / "sample_submission.tif"
    with rasterio.open(
        tpl_path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=float("nan"),
    ) as dst:
        dst.write(tpl_arr, 1)

    cat = np.zeros((h, w), dtype=np.uint8)
    cat[15:30, 20] = 1  # NW vertical segment
    cat[20, 50:68] = 1  # NE horizontal segment
    cat[55:72, 22] = 1  # SW vertical segment
    cat[60, 48:66] = 1  # SE horizontal segment
    cat_path = tmp_path / "catalogue_mask.tif"
    with rasterio.open(
        cat_path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=1,
        dtype="uint8",
        crs="EPSG:32611",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(cat, 1)

    return tpl_path, cat_path, footprint, cat > 0


def test_segment_buffered_folds_partition_cleanly(tmp_path: Path) -> None:
    _, _, footprint, cat_mask = _make_mini_template_and_cat(tmp_path)
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=6.0)
    assert len(folds) == 4
    union_withheld = np.zeros_like(cat_mask)
    total_withheld = 0
    for f in folds:
        assert not np.any(f.withheld_faults & f.visible_faults)
        assert not np.any(f.visible_faults & f.buffer_mask)
        assert not np.any(f.withheld_faults & f.buffer_mask)
        union_withheld |= f.withheld_faults
        total_withheld += f.n_withheld
    assert total_withheld == int(cat_mask.sum())
    assert np.array_equal(union_withheld, cat_mask)


def test_leakage_canary_flags_leaked_distance_and_passes_clean(tmp_path: Path) -> None:
    _, _, footprint, cat_mask = _make_mini_template_and_cat(tmp_path)
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=5.0)
    rng = np.random.default_rng(7)
    n_fp = int(footprint.sum())
    clean_x = rng.normal(size=(n_fp, 2)).astype(np.float32)

    res_clean = EH.run_leakage_canary(clean_x, ["f_noise1", "f_noise2"], folds, footprint, subsample_step=1)
    assert res_clean["all_pass"] is True
    assert res_clean["worst_symmetric_auc"] < 0.90

    leaked_dist = ndi.distance_transform_edt(~cat_mask).astype(np.float32)[footprint][:, None]
    res_leak = EH.run_leakage_canary(
        np.hstack([clean_x, -leaked_dist]),
        ["f_noise1", "f_noise2", "dist_known_fault_px_LEAK"],
        folds,
        footprint,
        subsample_step=1,
    )
    assert res_leak["all_pass"] is False
    assert "dist_known_fault_px_LEAK" in res_leak["flagged_features"]


def test_pooled_holdout_and_submodular_beats_ribbon(tmp_path: Path) -> None:
    _, _, footprint, cat_mask = _make_mini_template_and_cat(tmp_path)
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=5.0)

    # Smooth probability ridge centered on all faults (including withheld ones)
    d_true = ndi.distance_transform_edt(~cat_mask).astype(np.float32)
    prob = (0.75 * np.exp(-(d_true**2) / (2.0 * 1.8**2))).astype(np.float32)

    # Ribbon top-K vs Submodular 300m allocator with identical dot count (20 dots total across 4 folds)
    sub_preds: dict[int, np.ndarray] = {}
    rib_preds: dict[int, np.ndarray] = {}
    for f in folds:
        eligible = footprint & (~f.visible_faults) & (~f.buffer_mask) & f.region_mask
        sub_preds[f.fold_id] = DD.submodular_dti_emit(prob, eligible_mask=eligible, n_dots=5)

        rib = np.zeros_like(prob)
        idx = np.flatnonzero(eligible)
        top5 = idx[np.argsort(prob.ravel()[idx])[::-1][:5]]
        rib.ravel()[top5] = 1.0
        rib_preds[f.fold_id] = rib

    res_sub = EH.score_pooled_holdout(sub_preds, folds, footprint, n_boot=40, seed=11)
    res_rib = EH.score_pooled_holdout(rib_preds, folds, footprint, n_boot=40, seed=11)
    assert res_sub["metric_label"] == "HOLDOUT-DTI"
    assert res_sub["evaluator_version"] == EH.EVALUATOR_VERSION
    assert res_sub["n_withheld_positives"] == int(cat_mask.sum())
    assert res_sub["holdout_dti"] > res_rib["holdout_dti"]


def test_registry_uniqueness_catches_clone_and_passes_novel(tmp_path: Path) -> None:
    tpl_path, _, footprint, _ = _make_mini_template_and_cat(tmp_path)
    reg_dir = tmp_path / "reg"
    reg_dir.mkdir()

    r0 = np.zeros(footprint.shape, dtype=np.float32)
    r0[35, 35] = 1.0
    r0[40, 40] = 1.0
    r0[45, 45] = 1.0
    r0_path = reg_dir / "r0.tif"
    with rasterio.open(tpl_path) as src:
        profile = src.profile.copy()
    profile.update(nodata=None)
    with rasterio.open(r0_path, "w", **profile) as dst:
        dst.write(r0, 1)

    dup_check = EH.check_registry_uniqueness(r0[footprint], r0, footprint, [r0_path], corr_stride=1)
    assert dup_check["uniqueness_pass"] is False

    novel = np.zeros(footprint.shape, dtype=np.float32)
    novel[12, 60] = 1.0
    novel[68, 12] = 1.0
    novel[70, 70] = 1.0
    surface_check = EH.check_registry_surface_uniqueness(
        (novel * 0.5)[footprint], footprint, [r0_path], corr_stride=1
    )
    assert surface_check["phase"] == "pre-placement continuous surface"
    assert surface_check["uniqueness_pass"] is True

    ok_check = EH.check_registry_uniqueness((novel * 0.5)[footprint], novel, footprint, [r0_path], corr_stride=1)
    assert ok_check["uniqueness_pass"] is True


def test_registry_uniqueness_uses_literal_directed_overlap_for_dense_reference(tmp_path: Path) -> None:
    """A dense registry cannot switch the stated candidate->registry rule to F1."""
    tpl_path, _, footprint, _ = _make_mini_template_and_cat(tmp_path)
    with rasterio.open(tpl_path) as src:
        profile = src.profile.copy()
    profile.update(nodata=None)

    dense = footprint.astype(np.float32)
    dense_path = tmp_path / "dense-lattice.tif"
    with rasterio.open(dense_path, "w", **profile) as dst:
        dst.write(dense, 1)

    candidate = np.zeros(footprint.shape, dtype=np.float32)
    candidate[12, 12] = 1.0
    candidate[35, 35] = 1.0
    candidate[68, 68] = 1.0
    result = EH.check_registry_uniqueness(
        (candidate * 0.5)[footprint], candidate, footprint, [dense_path], corr_stride=1
    )
    comp = result["comparisons"][0]
    assert comp["cand_within_3px_of_reg"] == 1.0
    assert comp["effective_dot_overlap_3px"] == 1.0
    assert result["uniqueness_pass"] is False
    assert result["dot_overlap_policy"].startswith("strict directed")


def test_gdr_blind_geothermometer_parser_handles_whitespace_and_blind_90c(tmp_path: Path) -> None:
    csv_p = tmp_path / "gdr.csv"
    with open(csv_p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["row", "col", "thermalclass", "geothermquartz_c", "geothermchalc_c", "geothermcat_c", "dist_known_fault_px"])
        w.writerow([10, 12, "Hot ", "NULL", "NULL", "NULL", "0.0"])  # trailing space Hot!
        w.writerow([20, 22, "Cold", "118.4", "95.0", "NULL", "0.0"])  # blind >= 90 C!
        w.writerow([30, 32, "Cold", "42.0", "NULL", "NULL", "0.0"])  # true cold < 90 C

    masks = DD.extract_gdr_blind_and_thermal_cells(csv_p, (50, 50))
    assert bool(masks["hot_warm"][10, 12]) is True
    assert int(masks["hot_warm"].sum()) == 1
    assert bool(masks["blind_geotherm90"][20, 22]) is True
    assert int(masks["blind_geotherm90"].sum()) == 1


def test_submission_writer_enforces_range_0_1_collar_and_zip_sha(tmp_path: Path) -> None:
    tpl_path, cat_path, footprint, cat_mask = _make_mini_template_and_cat(tmp_path)
    d_cat = ndi.distance_transform_edt(~cat_mask)

    valid_dots = np.zeros(footprint.shape, dtype=np.float32)
    far_pts = np.argwhere(footprint & (d_cat > 4.5))
    for r, c in far_pts[:25:3]:
        valid_dots[r, c] = 1.0

    # Inject a NaN outside footprint to prove writer scrubs & emits clean zeros/nan twins
    valid_dots[0, 0] = np.nan

    rel_dir = tmp_path / "artifacts"
    dl_dir = tmp_path / "downloads"
    audit = SW.write_validated_submission_bundle(
        valid_dots,
        stem_prefix="test-h91",
        date_tag="20261024T000000Z",
        template_path=tpl_path,
        catalogue_path=cat_path,
        releases_dir=rel_dir,
        downloads_dir=dl_dir,
        floor_px=3.0,
        bundle_js_filename="test-custom-submission.js",
    )
    assert audit["browser_tif_bundle"]["path"].endswith("test-custom-submission.js")
    assert (dl_dir / "test-custom-submission.js").is_file()
    assert audit["validators"]["gems91_gates_verdict"] == "CERTIFIED"
    assert audit["validators"]["range_0_1_portal_safe"] is True
    assert audit["primary_zeros_tif"]["nan_cells_anywhere"] == 0
    assert audit["primary_zeros_tif"]["nodata"] is None
    assert 0.0 <= audit["primary_zeros_tif"]["min_value"] <= audit["primary_zeros_tif"]["max_value"] <= 1.0

    # Verify ZIP inner GeoTIFF byte-for-byte matches primary -zeros.tif
    z_tif_bytes = (rel_dir / audit["primary_zeros_tif"]["filename"]).read_bytes()
    with zipfile.ZipFile(dl_dir / audit["zip_bundle"]["filename"], "r") as zf:
        assert zf.namelist() == [audit["primary_zeros_tif"]["filename"]]
        assert zf.read(audit["primary_zeros_tif"]["filename"]) == z_tif_bytes

    # Out-of-range > 1.0 must fail closed
    bad_gt1 = valid_dots.copy()
    bad_gt1[far_pts[0][0], far_pts[0][1]] = 1.25
    with pytest.raises(ValueError, match="range violation"):
        SW.write_validated_submission_bundle(
            bad_gt1,
            stem_prefix="bad-gt1",
            date_tag="20261024T000000Z",
            template_path=tpl_path,
            catalogue_path=cat_path,
            releases_dir=rel_dir,
            downloads_dir=None,
        )

    # Collar violation (<= 3.0 px from catalogue) must fail closed
    bad_collar = valid_dots.copy()
    near_pt = np.argwhere(footprint & (~cat_mask) & (d_cat <= 2.0))[0]
    bad_collar[near_pt[0], near_pt[1]] = 1.0
    with pytest.raises(RuntimeError):
        SW.write_validated_submission_bundle(
            bad_collar,
            stem_prefix="bad-collar",
            date_tag="20261024T000000Z",
            template_path=tpl_path,
            catalogue_path=cat_path,
            releases_dir=rel_dir,
            downloads_dir=None,
        )


def test_certified_run_card_bundle_and_pages_site_integrity() -> None:
    import base64
    import hashlib
    import html
    import io
    import json
    import re
    import subprocess

    rc_ev = json.loads((ROOT / "evidence" / "run_card.json").read_text(encoding="utf-8"))
    rc_docs = json.loads((ROOT / "docs" / "data" / "run_card.json").read_text(encoding="utf-8"))
    assert rc_ev == rc_docs

    js_raw = (ROOT / "docs" / "data" / "run_card.js").read_text(encoding="utf-8")
    assert js_raw.startswith("window.GEMS91_RUN_CARD = ")
    rc_js = json.loads(js_raw[len("window.GEMS91_RUN_CARD = ") :].rstrip(";\n "))
    assert rc_js == rc_ev

    # Protocol Rule 1-6 invariants
    assert rc_ev["historical_verdict_before_directed_gate_fix"] == "promote"
    assert rc_ev["verdict"] == "negative"
    assert rc_ev["ok_to_download_and_submit"] is False
    assert rc_ev["current_policy_revalidation"]["status"] == "FAIL"
    assert rc_ev["budget"]["experiments_run"] <= 3
    assert rc_ev["budget"]["wall_clock_seconds"] <= 7200
    assert rc_ev["leakage_canary"]["all_pass"] is True
    assert rc_ev["leakage_canary"]["worst_symmetric_auc"] <= 0.90
    assert rc_ev["registry_uniqueness"]["historical_v1_0_uniqueness_pass"] is True
    assert rc_ev["registry_uniqueness"]["uniqueness_pass"] is False
    assert rc_ev["registry_uniqueness"]["uniqueness_gate_version"] == "gems91-directed-registry-v1.1"
    assert rc_ev["registry_uniqueness"]["max_surface_abs_rank_corr"] <= 0.90
    assert rc_ev["registry_uniqueness"]["max_3px_dot_overlap"] > 0.70

    sub = rc_ev["submission"]
    assert 1 <= len(sub["recommended_form_note"]) <= 140
    assert sub["recommended_form_note_length"] == len(sub["recommended_form_note"])
    assert sub["all_12279160_cells_finite"] is True
    assert sub["nodata_zeros_tif"] is None
    assert sub["min_value"] == 0.0
    assert sub["max_value"] == 1.0
    assert sub["dots_le_3px"] == 0
    assert sub["min_catalogue_distance_px"] > 3.0

    # Decode browser JS GeoTIFF bundle & compare byte-for-byte with ZIP & SHA-256
    bundle_txt = (ROOT / "docs" / "downloads" / "h91_submission_bundle.js").read_text(encoding="utf-8")
    payload_line = [ln for ln in bundle_txt.splitlines() if ln.startswith("window.GEMS91_SUBMISSION_BUNDLE = ")]
    assert len(payload_line) == 1
    bundle_obj = json.loads(payload_line[0][len("window.GEMS91_SUBMISSION_BUNDLE = ") :].rstrip(";\n "))
    tif_bytes = base64.b64decode(bundle_obj["primary_zeros"]["base64"])
    assert len(tif_bytes) == sub["bytes_zeros_tif"]
    assert hashlib.sha256(tif_bytes).hexdigest() == sub["sha256_zeros_tif"]

    nan_bytes = base64.b64decode(bundle_obj["companion_nan"]["base64"])
    assert hashlib.sha256(nan_bytes).hexdigest() == sub["sha256_nan_tif"]

    zip_path = ROOT / "docs" / "downloads" / sub["recommended_zip_download"]
    assert zip_path.exists()
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == sub["sha256_zeros_zip"]
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [sub["recommended_upload_file"]]
        assert zf.read(sub["recommended_upload_file"]) == tif_bytes

    # Inspect decoded GeoTIFF raster directly in memory via rasterio MemoryFile
    with rasterio.MemoryFile(io.BytesIO(tif_bytes)) as memfile:
        with memfile.open() as ds:
            assert ds.count == 1
            assert (ds.height, ds.width) == (3730, 3292)
            assert ds.dtypes[0] == "float32"
            assert str(ds.crs) == "EPSG:32611"
            assert ds.nodata is None
            arr = ds.read(1)
            assert np.isfinite(arr).all()
            assert float(arr.min()) == 0.0
            assert float(arr.max()) == 1.0
            assert int((arr > 0).sum()) == sub["n_dots"]

    # Check direct downloadable GeoTIFF in docs/downloads/ matches bundle & policy
    direct_tif = ROOT / "docs" / "downloads" / sub["recommended_upload_file"]
    assert direct_tif.exists()
    assert direct_tif.read_bytes() == tif_bytes

    # Check H91 GitHub Pages HTML files and local asset links
    for html_rel in [
        Path("docs/h91-ddvtc.html"),
        Path("docs/h91-executive-summary.html"),
    ]:
        hp = ROOT / html_rel
        assert hp.exists(), f"Missing {html_rel}"
        html_txt = hp.read_text(encoding="utf-8")
        assert sub["candidate_id"] in html_txt
        assert sub["sha256_zeros_tif"] in html_txt
        assert sub["recommended_form_note"] in html.unescape(html_txt)
        for attr_match in re.finditer(r'(?:href|src)="([^"]+)"', html_txt):
            target = attr_match.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                continue
            clean_rel = target.split("#", 1)[0].split("?", 1)[0]
            if not clean_rel:
                continue
            resolved = (hp.parent / clean_rel).resolve()
            assert resolved.exists(), f"Broken link {target!r} in {html_rel} -> {resolved}"
            rel_to_root = resolved.relative_to(ROOT)
            ign = subprocess.run(
                ["git", "check-ignore", "-q", str(rel_to_root)], cwd=ROOT
            )
            assert ign.returncode != 0, f"GitHub Pages asset {rel_to_root} is gitignored!"

    # Main portal links directly to H91 pages
    main_idx = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "h91-ddvtc.html" in main_idx and "h91-executive-summary.html" in main_idx


