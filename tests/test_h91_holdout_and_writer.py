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


def test_registry_uniqueness_catches_clone_and_fails_closed_on_partial_inventory(tmp_path: Path) -> None:
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
    assert dup_check["is_duplicate"] is True
    assert dup_check["uniqueness_pass"] is False
    assert dup_check["registry_inventory_complete"] is False
    assert dup_check["dots_max_3px_overlap"] == 1.0

    novel = np.zeros(footprint.shape, dtype=np.float32)
    novel[12, 60] = 1.0
    novel[68, 12] = 1.0
    novel[70, 70] = 1.0
    ok_check = EH.check_registry_uniqueness((novel * 0.5)[footprint], novel, footprint, [r0_path], corr_stride=1)
    assert ok_check["is_duplicate"] is False
    # A local path list is not a complete registry certificate, even when no
    # duplicate was observed in the one available raster.
    assert ok_check["uniqueness_pass"] is False
    assert ok_check["registry_inventory_complete"] is False

    # The shared comparator returns both metrics for any array. A broad-valued
    # continuous surface can have 100% positive-support overlap with a dense
    # reference; only its full-footprint rank correlation is binding here.
    smooth = np.zeros(footprint.shape, dtype=np.float32)
    smooth[footprint] = np.linspace(0.001, 0.999, int(footprint.sum()), dtype=np.float32)
    dense = np.zeros_like(smooth)
    dense[footprint] = 1.0
    dense_path = reg_dir / "dense-surface-reference.tif"
    with rasterio.open(dense_path, "w", **profile) as dst:
        dst.write(dense, 1)
    surface_check = EH.check_registry_uniqueness(smooth, np.zeros_like(novel), footprint, [dense_path])
    assert surface_check["surface_rank_duplicate"] is False
    assert surface_check["dot_overlap_duplicate"] is False
    assert surface_check["is_duplicate"] is False
    assert surface_check["uniqueness_pass"] is False  # inventory remains partial
    assert surface_check["surface_report"]["protocol_phase"] == "continuous_surface"
    surface_measurement = surface_check["surface_report"]["measurements"][0]
    assert surface_measurement["positive_support_overlap_diagnostic_only"] == 1.0
    assert surface_measurement["surface_rank_duplicate"] is False
    assert "duplicate_count" not in surface_check["surface_report"]
    assert surface_check["dots_report"]["protocol_phase"] == "final_candidate_dots"
    assert surface_check["dots_report"]["measurements"][0]["dot_overlap_duplicate"] is False

    # An undefined Spearman comparison against a constant registry raster is
    # not a uniqueness pass, even with a complete hash-verified test inventory.
    import hashlib

    empty_path = reg_dir / "empty-reference.tif"
    with rasterio.open(empty_path, "w", **profile) as dst:
        dst.write(np.zeros_like(smooth), 1)
    complete_test_index = {
        "complete_accessible_scan": True,
        "errors": [],
        "rasters": [{
            "repo_first": "test fixture",
            "sources": [empty_path.name],
            "cache_file": str(empty_path),
            "sha256": hashlib.sha256(empty_path.read_bytes()).hexdigest(),
        }],
    }
    unverified_check = EH.check_registry_uniqueness(smooth, novel, footprint, complete_test_index)
    assert unverified_check["registry_inventory_complete"] is True
    assert unverified_check["is_duplicate"] is False
    assert unverified_check["registry_measurement_unverified"]
    assert unverified_check["uniqueness_pass"] is False


def test_literal_directed_overlap_has_no_dense_reference_exception(tmp_path: Path) -> None:
    tpl_path, _, footprint, _ = _make_mini_template_and_cat(tmp_path)
    reg_dir = tmp_path / "reg"
    reg_dir.mkdir()
    with rasterio.open(tpl_path) as src:
        profile = src.profile.copy()
    profile.update(nodata=None)

    dense = np.zeros(footprint.shape, dtype=np.float32)
    dense[10:70, 10:70] = 1.0
    dense_path = reg_dir / "dense.tif"
    with rasterio.open(dense_path, "w", **profile) as dst:
        dst.write(dense, 1)

    candidate = np.zeros_like(dense)
    candidate[20, 20] = candidate[40, 40] = candidate[60, 60] = 1.0
    report = EH.check_registry_uniqueness(candidate[footprint], candidate, footprint, [dense_path])
    assert report["is_duplicate"] is True
    assert report["dots_max_3px_overlap"] == 1.0
    assert report["uniqueness_pass"] is False


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
    )
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


def test_negative_run_card_artifact_and_pages_integrity() -> None:
    import base64
    import hashlib
    import html
    import io
    import json
    import re
    import subprocess

    subprocess.run([sys.executable, "scripts/build_pages_site.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/render_portal.py"], cwd=ROOT, check=True)

    rc_ev = json.loads((ROOT / "evidence" / "run_card.json").read_text(encoding="utf-8"))
    rc_docs = json.loads((ROOT / "docs" / "data" / "run_card.json").read_text(encoding="utf-8"))
    assert rc_ev == rc_docs

    js_raw = (ROOT / "docs" / "data" / "run_card.js").read_text(encoding="utf-8")
    assert js_raw.startswith("window.GEMS91_RUN_CARD = ")
    rc_js = json.loads(js_raw[len("window.GEMS91_RUN_CARD = ") :].rstrip(";\n "))
    assert rc_js == rc_ev

    # A negative run card is explicit; technical PASS never overrides novelty.
    assert rc_ev["verdict"] == "negative"
    assert rc_ev["ok_to_download_and_submit"] is False
    assert rc_ev["ok_to_download_for_research"] is True
    assert rc_ev["ok_to_submit"] is False
    assert rc_ev["budget"]["experiments_run"] == 3
    assert rc_ev["budget"]["experiments_run"] <= rc_ev["budget"]["max_experiments"] <= 3
    assert rc_ev["budget"]["wall_clock_seconds"] <= 7200
    assert rc_ev["leakage_canary"]["all_pass"] is True
    assert rc_ev["leakage_canary"]["worst_symmetric_auc"] <= 0.90
    uniq = rc_ev["registry_uniqueness"]
    witness = uniq["direct_lattice_witness"]
    assert uniq["complete_accessible_scan"] is False
    assert uniq["uniqueness_pass"] is False
    assert uniq["is_duplicate"] is True
    assert witness["candidate_dots_within_3px"] == 38302
    assert witness["candidate_dots"] == 38400
    assert witness["directed_overlap"] == pytest.approx(38302 / 38400)
    assert witness["directed_overlap"] > witness["overlap_limit_strict_greater_than"]
    assert witness["continuous_surface_spearman_full_footprint"] is None
    assert witness["continuous_surface_correlation_status"] == "UNVERIFIED"
    assert rc_ev["submission_action"].startswith("NOT OK TO SUBMIT;")
    assert rc_ev["promotion_blockers"]
    assert "not promoted" in rc_ev["winning_experiment_status"]

    # Scores retain their evidence class and comparability boundary.
    holdout = rc_ev["scores"]["primary_holdout"]
    assert holdout["label"] == "HOLDOUT-DTI"
    assert holdout["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert holdout["n_withheld_positives"] == 60988
    assert len(holdout["ci_95"]) == 2
    assert "not comparable" in holdout["comparability"]
    assert rc_ev["scores"]["fleet_benchmark_reference"]["label"] == "USER-REPORTED-UNVERIFIED"

    sub = rc_ev["submission"]
    assert sub["status"] == "RESEARCH-ONLY; NOT OK TO SUBMIT"
    assert 1 <= len(sub["submission_note"]) <= 140
    assert sub["submission_note_length"] == len(sub["submission_note"])
    assert sub["all_cells_finite"] is True
    assert sub["nodata_zeros_tif"] is None
    assert sub["min_value"] == 0.0
    assert sub["max_value"] == 1.0
    assert sub["dots_le_3px"] == 0
    assert sub["min_catalogue_distance_px"] > 3.0
    assert sub["validator_results"]["format_report_ok"] is True
    assert sub["validator_results"]["vendor_template_validate_all_checks_passed"] is True
    assert all(sub["validator_results"]["vendor_template_checks"].values())
    assert sub["writer_validators"]["gems91_gates_verdict"] == "CERTIFIED"
    assert all(sub["writer_validators"][key] is True for key in (
        "release_gates_nan_pass", "release_gates_zeros_pass",
        "validate_raster_nan_pass", "validate_raster_zeros_pass", "range_0_1_portal_safe"))

    # Post-hoc evidence must bind to both stored research artifacts and the pinned template.
    re_audit = json.loads((ROOT / "evidence" / "h91_lattice_reaudit_20261024.json").read_text(encoding="utf-8"))
    assert re_audit["registry_witness"]["git_blob_sha1"] == "81c802618e6d46c6d62289d856ae74439439bbc6"
    assert re_audit["method_source"]["git_blob_sha1"] == "478c9001dc9c323cd50ba820f53c71dc2f80f221"
    assert hashlib.sha256((ROOT / "vendor/gems57/uniqueness.py").read_bytes()).hexdigest() == re_audit["method_source"]["sha256"]
    assert re_audit["artifacts"][0]["witness_comparison"]["directed_overlap"] == pytest.approx(38302 / 38400)
    assert re_audit["artifacts"][1]["witness_comparison"]["directed_overlap"] == pytest.approx(31972 / 32000)
    registry_summary = json.loads((ROOT / "evidence" / "registry_uniqueness.json").read_text(encoding="utf-8"))
    assert registry_summary["is_duplicate"] is True
    assert registry_summary["uniqueness_pass"] is False
    assert registry_summary["complete_accessible_scan"] is False
    assert registry_summary["h91_literal_lattice_witness"]["continuous_surface_spearman_full_footprint"] is None
    assert registry_summary["h91_literal_lattice_witness"]["continuous_surface_correlation_status"] == "UNVERIFIED"

    tif_path = ROOT / "docs" / "downloads" / sub["research_tif"]
    tif_bytes = tif_path.read_bytes()
    assert hashlib.sha256(tif_bytes).hexdigest() == sub["sha256_tif"]
    assert len(tif_bytes) == sub["bytes_tif"]

    # The historical browser bundle, ZIP and direct GeoTIFF all carry identical bytes.
    bundle_txt = (ROOT / "docs" / "downloads" / "h91_submission_bundle.js").read_text(encoding="utf-8")
    payload_line = [ln for ln in bundle_txt.splitlines() if ln.startswith("window.GEMS91_SUBMISSION_BUNDLE = ")]
    assert len(payload_line) == 1
    bundle_obj = json.loads(payload_line[0][len("window.GEMS91_SUBMISSION_BUNDLE = ") :].rstrip(";\n "))
    bundled_tif = base64.b64decode(bundle_obj["primary_zeros"]["base64"])
    assert bundled_tif == tif_bytes
    assert hashlib.sha256(base64.b64decode(bundle_obj["companion_nan"]["base64"])).hexdigest() == sub["sha256_nan_tif"]

    zip_path = ROOT / "docs" / "downloads" / sub["research_zip"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == sub["sha256_zip"]
    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_bytes

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

    # Both H91 pages use a visibly negative, research-only verdict and valid local links.
    for html_rel in (Path("docs/h91-ddvtc.html"), Path("docs/h91-executive-summary.html")):
        hp = ROOT / html_rel
        html_txt = hp.read_text(encoding="utf-8")
        decoded = html.unescape(html_txt)
        assert sub["candidate_id"] in decoded
        assert sub["sha256_tif"] in decoded
        assert "OK TO SUBMIT: NO" in decoded
        assert "DUPLICATE" in decoded
        assert "0.174030" in decoded
        assert "gems91-hide-recover-v1.0" in decoded
        assert "PROMOTED" not in decoded
        assert "20/20 REAL RASTERS UNIQUE" not in decoded
        assert "drivendata.org/competitions/306/competition-doe-gems/submissions" not in decoded
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
            ign = subprocess.run(["git", "check-ignore", "-q", str(rel_to_root)], cwd=ROOT)
            assert ign.returncode != 0, f"GitHub Pages asset {rel_to_root} is gitignored!"

    main_idx = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "h91-ddvtc.html" in main_idx and "h91-executive-summary.html" in main_idx
    assert "NOT OK TO SUBMIT" in main_idx
    assert "99.7448%" in main_idx

    for item in json.loads((ROOT / "registry/artifact_policy.json").read_text())["files"]:
        if "ddvtc" in item["path"].lower():
            assert item["status"] == "current_research_only"
            assert "DUPLICATE" in item["reason"]

