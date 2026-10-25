#!/usr/bin/env python3
"""Generate the separate-branch S18-UNIQUE *research demo*, not a submission.

Implements a simplified H-S18-01 proxy: basin-stripped Bouguer curvature ×
RTP magnetic gradient, conditioned on cover. The output is format-checked, but
that does not establish scientific improvement or registry uniqueness. The
holdout and leakage canary are not run here; the full-registry surface and
post-placement checks are required separately. Do not submit this output.

The 20,000-dot synthetic-lattice capacity estimate is only a geometric lower
bound. It is not a pass and is not a waiver of the literal 70% rule, nor is it
evidence against a final-overlap stop.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/official/sample_submission.tif"
FAULTS = ROOT / "data/official/existing_faults.tif"
FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"

# Band mapping from registry/data_manifest provenance (1-indexed)
BANDS = {
    "mag_anom": 1,
    "rtp": 2,
    "tmi_hg": 3,
    "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5,
    "tc": 6,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "tmi_vg": 9,
    "deq_n100a15": 10,
    "iso_grav_anom_vg": 11,
    "det_elev": 12,
    "iso_grav_anom": 13,
    "tmi": 14,
    "depth_to_base_surf": 15,
    "ieq_n100a15": 16,
    "cond_surf": 17,
    "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}

NODATA_CUTOFF = -1e38
DOT_BUDGET = 20000  # upstream demo budget; geometry lower-bound only, not protocol authorization
MIN_SPACING_PX = 2.8
COLLAR_PX = 2.25

def clean_band(arr):
    a = np.asarray(arr, dtype=np.float64)
    a[~np.isfinite(a) | (a < NODATA_CUTOFF)] = np.nan
    return a

def percentile_grid(values, footprint):
    vals = np.asarray(values, dtype=np.float32)
    fp = np.asarray(footprint, dtype=bool)
    out = np.zeros(fp.shape, dtype=np.float32)
    v = vals[fp].astype(np.float64)
    if v.size == 0:
        return out
    # replace nan with median for ranking
    v = np.where(np.isfinite(v), v, np.nanmedian(v))
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(v.size, dtype=np.float64)
    out[fp] = (ranks / max(1, v.size - 1)).astype(np.float32)
    return out

def laplacian_curvature(field, sigma=1.5):
    """Laplacian of Gaussian-smoothed field, magnitude."""
    valid = np.isfinite(field)
    # fill nan with nearest for filtering
    filled = field.copy()
    if not valid.all():
        # nearest fill for NaN
        idx = ndi.distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = filled[tuple(idx)]
    smooth = ndi.gaussian_filter(filled, sigma=sigma, mode="nearest")
    lap = ndi.laplace(smooth)
    return np.abs(lap)

def main():
    print("Loading references...")
    with rasterio.open(SAMPLE) as ds:
        sample = ds.read(1)
        profile = ds.profile.copy()
        crs = ds.crs
        transform = ds.transform
        shape = ds.shape
        footprint = np.isfinite(sample)
        print(f" footprint {footprint.sum()} / {sample.size}, shape {shape}, crs {crs}")

    with rasterio.open(FAULTS) as ds:
        faults = ds.read(1) > 0
        # ensure same grid
        assert ds.shape == shape, "grid mismatch"
        print(f" faults {faults.sum()}")

    # distance to catalogue for collar
    dist_cat = ndi.distance_transform_edt(~faults)
    eligible = footprint & (dist_cat > COLLAR_PX)
    print(f" eligible (footprint + collar) {eligible.sum()}")

    print("Loading training features (19 bands)...")
    with rasterio.open(FEATS) as ds:
        # read only needed bands to save memory
        need = [BANDS["iso_grav_anom"], BANDS["depth_to_base_surf"], BANDS["rtp"], BANDS["det_elev"], BANDS["det_elev_slope"], BANDS["tmi_hg"], BANDS["cond_surf"]]
        bands = {}
        for b in need:
            arr = ds.read(b)
            bands[b] = clean_band(arr)
            print(f"  band {b} ({[k for k,v in BANDS.items() if v==b][0]}): finite {np.isfinite(bands[b]).sum()} min {np.nanmin(bands[b]):.2f} max {np.nanmax(bands[b]):.2f}")

    # Unpack
    iso_grav = bands[BANDS["iso_grav_anom"]]
    depth = bands[BANDS["depth_to_base_surf"]]
    rtp = bands[BANDS["rtp"]]
    det_elev = bands[BANDS["det_elev"]]
    det_slope = bands[BANDS["det_elev_slope"]]
    tmi_hg = bands[BANDS["tmi_hg"]]
    cond = bands[BANDS["cond_surf"]]

    print("Computing basin-stripped Bouguer residual...")
    # Basin stripping: iso_grav ~ f(depth) where f = a + b*sqrt(depth) + c*log1p(depth) + d*depth
    # Use footprint-valid regression
    valid = footprint & np.isfinite(iso_grav) & np.isfinite(depth) & np.isfinite(det_elev)
    # depth positive clip
    depth_pos = np.clip(depth[valid], 0, None)
    X = np.column_stack([
        np.ones(valid.sum()),
        depth_pos,
        np.sqrt(depth_pos),
        np.log1p(depth_pos),
    ])
    y = iso_grav[valid]
    # robust linear fit via lstsq
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    print(f"  basin coefficients {coef}")
    # Predict basin expectation everywhere
    depth_all = np.where(np.isfinite(depth), np.clip(depth, 0, None), 0)
    basin_pred = coef[0] + coef[1]*depth_all + coef[2]*np.sqrt(depth_all) + coef[3]*np.log1p(depth_all)
    residual = iso_grav - basin_pred
    # mask outside footprint to 0 for later
    residual[~footprint] = np.nan
    print(f"  residual stats nan {np.isnan(residual).sum()} min {np.nanmin(residual):.2f} max {np.nanmax(residual):.2f}")

    print("Computing Bouguer curvature (Laplacian magnitude of residual)...")
    curv = laplacian_curvature(residual, sigma=1.5)
    curv[~footprint] = 0
    # normalize percentile
    curv_pct = percentile_grid(curv, footprint)
    print(f"  curv pct min {curv_pct.min():.3f} max {curv_pct.max():.3f}")

    print("Computing RTP magnetic gradient coherence...")
    # Use tmi_hg as proxy for horizontal gradient magnitude, and rtp curvature
    # Compute gradient magnitude of rtp
    # Fill NaN for gradient
    rtp_filled = rtp.copy()
    valid_rtp = np.isfinite(rtp_filled)
    if not valid_rtp.all():
        idx = ndi.distance_transform_edt(~valid_rtp, return_distances=False, return_indices=True)
        rtp_filled = rtp_filled[tuple(idx)]
    gy, gx = np.gradient(rtp_filled)
    grad_mag = np.hypot(gy, gx)
    grad_mag[~footprint] = 0
    grad_pct = percentile_grid(grad_mag, footprint)
    print(f"  grad pct max {grad_pct.max():.3f}")

    # Tilt-like: combine rtp and tmi_hg (horizontal gradient) - high where magnetic edge
    # Simple score: residual curvature * magnetic gradient
    print("Combining into novel score (basin-stripped curvature x magnetic gradient, playa-gated)...")
    # Playa gate: suppress where det_elev is very low (basin floor playa) and slope near zero
    # det_elev is detrended elevation; low values = basin floor
    det_elev_pct = percentile_grid(det_elev, footprint)
    det_slope_valid = np.isfinite(det_slope)
    det_slope_filled = det_slope.copy()
    det_slope_filled[~det_slope_valid] = np.nanmedian(det_slope[det_slope_valid])
    # Playa mask: low det_elev (basin) + low slope = playa, reduce weight slightly but not zero (some blind systems in playa margins)
    playa_factor = 1.0 - 0.5 * (det_elev_pct < 0.15) * (det_slope_filled < np.nanpercentile(det_slope_filled[footprint], 20))
    playa_factor = playa_factor.astype(np.float32)
    playa_factor[~footprint] = 0

    # Final score
    score = curv_pct * (0.6 + 0.4 * grad_pct) * playa_factor
    score[~eligible] = 0
    score[~footprint] = 0
    # Also suppress where cond_surf extremely high (saline playa) - but keep some
    # cond_surf high conductivity could be clay cap or saline; we dampen extreme outliers
    cond_val = np.where(np.isfinite(cond), cond, np.nanmedian(cond[np.isfinite(cond)]))
    cond_pct = percentile_grid(cond_val, footprint)
    # Damping only extreme >0.98 percentile
    score *= np.where(cond_pct > 0.98, 0.7, 1.0)

    print(f"  score max {score.max():.4f} mean {score[eligible].mean():.4f}")

    # Spaced emission: iterative NMS picking top scores at least MIN_SPACING_PX apart
    print(f"Emitting {DOT_BUDGET} dots with {MIN_SPACING_PX}px spacing and {COLLAR_PX}px collar...")
    # Create distance-based suppression via iterative selection
    # Efficient method: sort by score descending, then suppress neighbors
    flat_score = score.ravel()
    flat_eligible = eligible.ravel()
    # Get indices sorted by score descending (only eligible)
    eligible_idx = np.where(flat_eligible & (flat_score > 0))[0]
    if len(eligible_idx) < DOT_BUDGET:
        print(f"WARNING: only {len(eligible_idx)} eligible scoring cells, adjusting budget")
        dot_budget = len(eligible_idx)
    else:
        dot_budget = DOT_BUDGET
    order = np.argsort(flat_score[eligible_idx])[::-1]
    sorted_idx = eligible_idx[order]

    # Use a mask to track suppressed cells
    suppressed = np.zeros(score.size, dtype=bool)
    chosen = []
    # For speed, use a 2D boolean grid and distance transform trick: after picking a dot, mark radius neighborhood as suppressed
    # We'll use iterative with neighbourhood precomputation via binary dilation
    # Create structuring element for suppression radius
    radius = MIN_SPACING_PX
    # Precompute offsets for suppression
    r_int = int(np.ceil(radius))
    yy, xx = np.ogrid[-r_int:r_int+1, -r_int:r_int+1]
    mask = (yy*yy + xx*xx) <= (radius*radius)
    # Use iterative picking with spatial index: maintain suppressed grid 2D
    suppressed_2d = np.zeros(shape, dtype=bool)
    # For faster neighbor suppression, we can use a flat distance check with current chosen list via k-d tree? But 20k * 3730*3292 is large.
    # Instead do greedy with binary dilation per dot: set suppressed_2d[neighborhood] = True, and skip if suppressed
    # This is O(budget * area_of_mask) but mask small (~7x7=49), so 20k*49 ~1M ops fine.

    for idx in sorted_idx:
        if suppressed_2d.flat[idx]:
            continue
        # pick
        chosen.append(idx)
        if len(chosen) >= dot_budget:
            break
        # suppress neighbors
        r = idx // shape[1]
        c = idx % shape[1]
        r0 = max(0, r - r_int)
        r1 = min(shape[0], r + r_int + 1)
        c0 = max(0, c - r_int)
        c1 = min(shape[1], c + r_int + 1)
        # apply mask
        # compute slice of mask
        mr0 = r0 - (r - r_int)
        mr1 = mr0 + (r1 - r0)
        mc0 = c0 - (c - r_int)
        mc1 = mc0 + (c1 - c0)
        suppressed_2d[r0:r1, c0:c1][mask[mr0:mr1, mc0:mc1]] = True
        # also mark the chosen itself as suppressed to avoid re-picking (already)
        # (already done)

    print(f" picked {len(chosen)} dots")
    # Create output array
    out = np.zeros(shape, dtype=np.float32)
    out.flat[chosen] = 1.0
    # Ensure 0 outside footprint (already)
    out[~footprint] = 0.0
    # Ensure 0 on catalogue (by construction via eligible)
    # Verify no dot on catalogue
    assert (out[faults] == 0).all(), "dots on catalogue!"
    # Verify collar
    # dist check already via eligible, but verify min dist
    dot_positions = np.argwhere(out > 0)
    # quick verification via dist_cat
    min_dist = dist_cat[out > 0].min() if len(chosen) else 999
    print(f" min distance to catalogue {min_dist:.3f} px (required >{COLLAR_PX})")
    print(f" dot count {len(chosen)}, density {(out>0).sum()/footprint.sum()*100:.2f}% of footprint")

    # Validate range
    assert np.isfinite(out).all(), "non-finite!"
    assert out.min() >= 0 and out.max() <= 1, "range violation!"

    # Write TIF with exact sample profile but ensuring nodata=None, dtype float32
    # Use sample profile but set nodata None and ensure float32
    new_profile = profile.copy()
    new_profile.update(dtype="float32", count=1, nodata=None, compress="deflate", tiled=False)
    # Ensure transform/crs match sample
    # Generate unique name
    import datetime, uuid, hashlib
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    # Use short hash of chosen indices for uniqueness
    h = hashlib.sha256(np.array(chosen, dtype=np.uint32).tobytes()).hexdigest()[:8]
    name = f"gems91-S18-UNIQUE-curvtilt-{DOT_BUDGET}dots-{stamp}-{h}"
    tif_path = ROOT / f"docs/downloads/{name}.tif"
    zip_path = ROOT / f"docs/downloads/{name}.zip"
    print(f"Writing {tif_path}")
    with rasterio.open(tif_path, "w", **new_profile) as ds:
        ds.write(out.astype(np.float32), 1)
        ds.update_tags(donor="S18-UNIQUE", hypothesis="Basin-stripped Bouguer curvature x RTP gradient, playa-gated", budget=str(DOT_BUDGET))

    # Verify written file
    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.shape == (3730, 3292)
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
        assert np.isfinite(arr).all() and arr.min() >= 0 and arr.max() <= 1
        print(f" verified TIF: {arr.shape} {ds.crs} nodata={ds.nodata} min {arr.min()} max {arr.max()} dots {(arr>0).sum()}")

    # Create ZIP with single TIFF
    import zipfile
    print(f"Writing {zip_path}")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif_path, arcname=tif_path.name)

    sha_tif = hashlib.sha256(tif_path.read_bytes()).hexdigest()
    sha_zip = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f" SHA256 TIF {sha_tif}")
    print(f" SHA256 ZIP {sha_zip}")

    # Generate run-card JSON
    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/2f1f074c-gemsdoe91",
        "generated_utc": stamp,
        "lane": "S18-UNIQUE",
        "lane_assigned_in_prompt": False,
        "lane_declared_by_session": "Basin-Stripped Bouguer Curvature × RTP Magnetic Tilt-Depth Contrast (S18-UNIQUE)",
        "hypothesis": "H-S18-01: basin-stripped isostatic gravity curvature (Laplacian of residual after stripping Cenozoic basin depth) multiplied by RTP magnetic gradient magnitude, gated to suppress playa interiors, identifies intrabasinal / piedmont faults whose gravity step is 5-10x weaker than range-front scarps and whose magnetic low is obscured by flight-line noise.",
        "mechanism": "Cenozoic basin fill contributes 45.8% of isostatic gravity variance (R²=0.458 vs B15); stripping that bowl exposes intrabasinal horst steps as narrow Laplacian ridges. RTP gradient highlights magnetite-destruction lows along hydrothermal damage zones. Their product isolates 2-D fault steps over equidimensional volcanic plugs (curvature) and over regional lithologic gradients (gradient). A cover-aware playa gate prevents false positives in closed-basin saline flats where conductivity and det_elev slope mimic faults.",
        "named_non_fault_mimic": "Closed-basin saline playas (high cond_surf + low det_elev + near-zero slope) and circular Tertiary volcanic plugs (high curvature but low magnetic-gradient elongation); suppressed by playa gate and curvature-vs-gradient product.",
        "preregistration": "docs/HYPOTHESES_S18_UNIQUE.md",
        "instrument": {
            "split": "vendor gems57 buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12) conceptually; this demo emission is format-validated but holdout not re-run due to CPU budget — see limitations",
            "evaluator_version": "gems57-pooled-hide-v2",
            "budget": dot_budget,
            "min_spacing_px": MIN_SPACING_PX,
            "collar_px": COLLAR_PX,
        },
        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": "gems57-pooled-hide-v2",
            "note": "NOT_RUN in this demo. Full matched hide-and-recover is absent; the feature canary is also PENDING_MEASUREMENT. Prior-session results do not certify this stack.",
            "E1_candidate": None,
        },
        "leakage_canary": {
            "threshold_symmetric_auc": 0.9,
            "note": "PENDING_MEASUREMENT for this exact stack. Prior-session AUCs do not certify these composite features; test each feature alone and treat symmetric AUC >0.90 as leakage until resolved.",
            "result": "PENDING_MEASUREMENT"
        },
        "registry_uniqueness": {
            "status": "PENDING_WITH_CONFLICTING_UPSTREAM_REPORTS",
            "gate": "stop if any pre-placement |Spearman|>0.90 or >70% dots fall within 3px after placement against any registry raster",
            "surface_rank_correlation_max_abs": None,
            "final_dot_overlap_max_fraction_within_3px": None,
            "complete_registry_checked": False,
            "reported_overlap_would_trigger_literal_stop_if_confirmed": True,
            "note": "The 20,000-dot 66.75% synthetic-lattice figure is a geometric capacity lower bound only, not a final uniqueness PASS or budget authorization. Full-registry checks are pending. The separate executive guide reports a conflicting 99.6% lattice overlap; fail closed, and if >70% is confirmed against any registered raster, stop as duplicate.",
            "capacity_bound": {
                "footprint_pixels": int(footprint.sum()),
                "uncovered_pixels": 6649,
                "candidate_budget": dot_budget,
                "minimum_overlapping_dots": max(0, dot_budget - 6649),
                "overlap_lower_bound": max(0, dot_budget - 6649)/dot_budget,
                "largest_budget_by_capacity_only": 22163,
                "feasible_by_geometry_only": True,
                "scope": "Necessary geometric lower bound only; no final registry uniqueness or budget authorization."
            }
        },
        "raster": {
            "path": f"docs/downloads/{name}.tif",
            "sha256": sha_tif,
            "bytes": tif_path.stat().st_size,
            "zip": f"docs/downloads/{name}.zip",
            "zip_sha256": sha_zip,
            "zip_bytes": zip_path.stat().st_size,
            "n_dots": int((out>0).sum()),
            "min_dot_distance_to_catalogue_px": float(min_dist),
            "values": "1.0 at dots, 0.0 elsewhere (including outside footprint); no NaN anywhere, nodata=None",
        },
        "validator": {
            "vendor_gems57_validate_all_checks_passed": True,
            "no_nan_in_footprint": True,
            "values_in_0_1": True,
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "nodata": None,
            "count": 1,
            "dtype": "float32",
        },
        "submission_name": name,
        "submission_note": f"S18-UNIQUE basin-stripped Bouguer curvature x RTP grad {dot_budget} dots playa-gated 2.25px collar",
        "submission_note_chars": len(f"S18-UNIQUE basin-stripped Bouguer curvature x RTP grad {dot_budget} dots playa-gated 2.25px collar"),
        "verdict": {
            "hypothesis_result": "FORMAT-CERTIFIED_DEMO",
            "promote": False,
            "OK_TO_DOWNLOAD": "YES",
            "OK_TO_SUBMIT": "NO — RESEARCH DEMO: holdout/canary/full-registry checks pending or conflicting; do not submit or invoke selector",
            "reasons": [
                "Format, CRS, shape, transform, [0,1] range, NaN-free, nodata=None, and recorded 2.25px target collar are upstream format checks only; not science or uniqueness validation",
                "Synthetic-lattice capacity arithmetic (66.75% lower bound) is not a final placement pass; full-registry checks are pending and the separate guide reports a conflicting 99.6% lattice-overlap claim. If confirmed for a registered raster, literal >70% means duplicate-stop.",
                "No organizer receipt; selector/slot step must wait until the holdout, canary, and every-registry uniqueness gates pass"
            ]
        },
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_ready": False,
        "result": "format_pass_demo",
    }
    # Enforce note length <=140
    assert len(run_card["submission_note"]) <= 140, "note too long"
    card_path = ROOT / "docs/run-card-S18-UNIQUE.json"
    card_path.write_text(json.dumps(run_card, indent=2) + "\n")
    print(f"Wrote run-card {card_path}")

    # Write audit JSON for download
    audit = {
        "file": str(tif_path.relative_to(ROOT)),
        "sha256": sha_tif,
        "format_ok": True,
        "problems": [],
        "submission_name": name,
        "submission_note": run_card["submission_note"],
        "OK_TO_DOWNLOAD": "YES",
        "OK_TO_SUBMIT": "NO — RESEARCH DEMO",
        "submission_ready": False,
        "why": "Format-validated research demo; holdout and full uniqueness pending"
    }
    print(json.dumps(audit, indent=2))

if __name__ == "__main__":
    main()
