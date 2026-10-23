"""RELIEF axis operator: count-fixed mass reallocation across Basin / Piedmont / Range-Front terciles.

Brief section 5 specification:
    RELIEF: shift 10-15% of mass between basin / piedmont / range-front terciles
    (relief from the detrended-elevation bands), count fixed.

Design invariants
-----------------
1. Relief terciles come exclusively from the competition-provided detrended-elevation
   bands of ``training_features``: Band 12 (``det_elev``, regional-trend-removed
   elevation, m) and Band 19 (``det_elev_slope``, detrended slope, deg).
2. Within-tercile dot ranking uses a relief-blind, label-blind subsurface structural
   score ``S_struct`` combining multi-line lineage corroboration (``anc_h19_5``,
   ``anc_h19_4``, ``anc_h16_1``) with potential-field fault-edge gradients
   (``tmi_hg``, ``iso_grav_anom_slope``, ``|iso_grav_anom_hg|``, ``tc``). Topographic
   bands are excluded from ``S_struct`` so within-tercile selection does not drift
   toward tercile boundaries, and ``existing_faults`` never enters ``S_struct``.
3. Both donor removal and recipient placement are restricted to ``d_cat > collar_px``
   (default 3.0 px = 300 m kernel radius), so R0's 2-3 px collar count is held
   strictly invariant (0 collar dots removed, 0 collar dots added).
4. Dot count (37,654) and unit mass ({0.0, 1.0}) are conserved exactly, and minimum
   nearest-neighbour spacing >= 2.0 px is enforced on all added dots.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

TERCILE_KEYS = ("basin", "pied", "range")


def fill_footprint_percentile(
    arr: np.ndarray,
    footprint: np.ndarray,
    *,
    sentinel: float = -1e30,
) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-neighbour fill of boundary sentinels inside ``footprint`` + [0, 1] rank."""
    fp = np.asarray(footprint, dtype=bool)
    a = np.asarray(arr, dtype=np.float64)
    valid = fp & np.isfinite(a) & (a > sentinel)
    if not valid.any():
        raise ValueError("feature band has no valid values inside footprint")
    if np.array_equal(valid, fp):
        filled = np.where(fp, a, np.nan)
    else:
        _, idx = ndi.distance_transform_edt(~valid, return_indices=True)
        filled = np.where(fp, a[idx[0], idx[1]], np.nan)
    pct = np.zeros(a.shape, dtype=np.float64)
    vals = filled[fp]
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(len(vals), dtype=np.float64)
    ranks[order] = np.arange(len(vals), dtype=np.float64) / max(1, len(vals))
    pct[fp] = ranks
    return pct, filled


def compute_relief_terciles(
    det_elev: np.ndarray,
    det_slope: np.ndarray,
    footprint: np.ndarray,
    *,
    w_elev: float = 0.90,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, object]]:
    """Partition ``footprint`` into Basin / Piedmont / Range-Front terciles."""
    if not (0.0 < w_elev <= 1.0):
        raise ValueError("w_elev must lie in (0, 1]")
    fp = np.asarray(footprint, dtype=bool)
    pct_elev, elev_filled = fill_footprint_percentile(det_elev, fp)
    pct_slope, slope_filled = fill_footprint_percentile(det_slope, fp)
    relief_idx = w_elev * pct_elev + (1.0 - w_elev) * pct_slope

    q33, q67 = (float(x) for x in np.quantile(relief_idx[fp], [1.0 / 3.0, 2.0 / 3.0]))
    terciles = {
        "basin": fp & (relief_idx <= q33),
        "pied": fp & (relief_idx > q33) & (relief_idx <= q67),
        "range": fp & (relief_idx > q67),
    }
    stats: dict[str, object] = {
        "formula": f"{w_elev:.2f}*pct(det_elev) + {1.0 - w_elev:.2f}*pct(det_elev_slope)",
        "q33": round(q33, 6),
        "q67": round(q67, 6),
        "terciles": {},
    }
    for key, mask in terciles.items():
        stats["terciles"][key] = {
            "footprint_px": int(mask.sum()),
            "footprint_pct": round(100.0 * float(mask.sum()) / max(1, int(fp.sum())), 3),
            "median_det_elev_m": round(float(np.nanmedian(elev_filled[mask])), 2),
            "median_det_slope_deg": round(float(np.nanmedian(slope_filled[mask])), 2),
        }
    return relief_idx, terciles, stats


def compute_structural_score(
    tmi_hg: np.ndarray,
    grav_slope: np.ndarray,
    grav_hg: np.ndarray,
    tc: np.ndarray,
    h195: np.ndarray,
    h194: np.ndarray,
    h161: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Relief-blind, label-blind structural score and potential-field crest mask."""
    fp = np.asarray(footprint, dtype=bool)
    p_tmi, _ = fill_footprint_percentile(tmi_hg, fp)
    p_gsl, _ = fill_footprint_percentile(grav_slope, fp)
    p_ghg, _ = fill_footprint_percentile(np.abs(grav_hg), fp)
    p_tc, _ = fill_footprint_percentile(tc, fp)

    pot = 0.35 * p_tmi + 0.30 * p_gsl + 0.25 * p_ghg + 0.10 * p_tc
    corrob = (
        np.asarray(h195, dtype=np.float64)
        + np.asarray(h194, dtype=np.float64)
        + np.asarray(h161, dtype=np.float64)
    ) / 3.0
    s_struct = 0.60 * corrob + 0.40 * pot

    pot_sm = ndi.gaussian_filter(pot, sigma=1.0, mode="nearest")
    crest_ns = np.zeros_like(fp)
    crest_ew = np.zeros_like(fp)
    crest_ns[1:-1, :] = (pot_sm[1:-1, :] >= pot_sm[:-2, :]) & (pot_sm[1:-1, :] > pot_sm[2:, :])
    crest_ew[:, 1:-1] = (pot_sm[:, 1:-1] >= pot_sm[:, :-2]) & (pot_sm[:, 1:-1] > pot_sm[:, 2:])
    pot_crest = (
        (crest_ns | crest_ew)
        & (p_tmi >= 0.80)
        & (np.maximum(p_gsl, p_ghg) >= 0.80)
        & fp
    )
    return s_struct, pot_crest


def shift_relief_mass(
    parent_dots: np.ndarray,
    terciles: dict[str, np.ndarray],
    dcat: np.ndarray,
    s_struct: np.ndarray,
    lineage_union: np.ndarray,
    pot_crest: np.ndarray,
    *,
    donor_key: str,
    recipient_key: str,
    frac: float = 0.12,
    collar_px: float = 3.0,
) -> dict[str, object]:
    """Shift ``frac`` of ``parent_dots`` from ``donor_key`` to ``recipient_key``."""
    if donor_key not in TERCILE_KEYS or recipient_key not in TERCILE_KEYS:
        raise ValueError(f"tercile keys must be in {TERCILE_KEYS}")
    if donor_key == recipient_key:
        raise ValueError("donor_key and recipient_key must differ")
    if not (0.10 <= frac <= 0.15):
        raise ValueError(f"RELIEF shift fraction must lie in [0.10, 0.15] per brief; got {frac}")

    p = np.asarray(parent_dots, dtype=bool)
    n_parent = int(p.sum())
    n_shift = int(round(frac * n_parent))
    if n_shift < 1:
        raise ValueError("shift count rounded to 0 dots")

    donor_pool = p & terciles[donor_key] & (dcat > collar_px)
    dys, dxs = np.nonzero(donor_pool)
    if len(dys) < n_shift:
        raise ValueError(
            f"donor tercile {donor_key!r} has only {len(dys)} off-collar dots (< {n_shift})"
        )

    # Deterministic removal: weakest structural score first, tie-break on (row, col)
    d_order = np.lexsort((dxs, dys, s_struct[dys, dxs]))[:n_shift]
    rem_y, rem_x = dys[d_order], dxs[d_order]
    surviving = p.copy()
    surviving[rem_y, rem_x] = False

    rec_mask = terciles[recipient_key] & (dcat > collar_px)
    lin_pool = np.asarray(lineage_union, dtype=bool) & rec_mask
    crest_pool = np.asarray(pot_crest, dtype=bool) & ~lin_pool & rec_mask

    occ = surviving.copy()
    tiers: dict[str, int] = {}
    added_y: list[int] = []
    added_x: list[int] = []

    for tier_name, cand_mask, min_sep in (
        ("lineage_d2p8", lin_pool, 2.8),
        ("lineage_d2p0", lin_pool, 2.0),
        ("geophys_crest_d2p8", crest_pool, 2.8),
    ):
        need = n_shift - len(added_y)
        if need <= 0:
            tiers[tier_name] = 0
            continue
        d_occ = ndi.distance_transform_edt(~occ)
        pool = cand_mask & ~occ & (d_occ >= min_sep - 1e-6)
        ys, xs = np.nonzero(pool)
        if len(ys) == 0:
            tiers[tier_name] = 0
            continue
        order = np.lexsort((xs, ys, -s_struct[ys, xs]))
        ys, xs = ys[order], xs[order]
        rr = int(np.ceil(min_sep))
        yy, xx = np.mgrid[-rr : rr + 1, -rr : rr + 1]
        disk = np.hypot(yy, xx) < (min_sep - 1e-6)
        cnt = 0
        h, w = occ.shape
        for y, x in zip(ys.tolist(), xs.tolist()):
            if len(added_y) >= n_shift:
                break
            y0, y1 = max(0, y - rr), min(h, y + rr + 1)
            x0, x1 = max(0, x - rr), min(w, x + rr + 1)
            sub_disk = disk[rr - (y - y0) : rr + (y1 - y), rr - (x - x0) : rr + (x1 - x)]
            if not (occ[y0:y1, x0:x1] & sub_disk).any():
                occ[y, x] = True
                added_y.append(y)
                added_x.append(x)
                cnt += 1
        tiers[tier_name] = cnt

    if len(added_y) != n_shift:
        raise RuntimeError(
            f"recipient tercile {recipient_key!r} placed {len(added_y)}/{n_shift} dots"
        )

    added_mask = occ & ~p
    removed_mask = p & ~occ
    assert int(occ.sum()) == n_parent
    assert int(added_mask.sum()) == n_shift == int(removed_mask.sum())
    assert int((added_mask & (dcat <= collar_px)).sum()) == 0
    assert int((removed_mask & (dcat <= collar_px)).sum()) == 0

    tercile_before = {k: int((p & m).sum()) for k, m in terciles.items()}
    tercile_after = {k: int((occ & m).sum()) for k, m in terciles.items()}
    return {
        "dots": occ,
        "donor_tercile": donor_key,
        "recipient_tercile": recipient_key,
        "frac_requested": frac,
        "n_parent": n_parent,
        "n_dots": int(occ.sum()),
        "n_shifted": n_shift,
        "pct_relocated": round(100.0 * n_shift / n_parent, 4),
        "pct_hamming": round(200.0 * n_shift / n_parent, 4),
        "recipient_tiers": tiers,
        "donor_s_struct_mean": round(float(s_struct[rem_y, rem_x].mean()), 6),
        "recipient_s_struct_mean": round(float(s_struct[added_y, added_x].mean()), 6),
        "tercile_counts_before": tercile_before,
        "tercile_counts_after": tercile_after,
        "tercile_pct_before": {
            k: round(100.0 * v / n_parent, 3) for k, v in tercile_before.items()
        },
        "tercile_pct_after": {
            k: round(100.0 * v / n_parent, 3) for k, v in tercile_after.items()
        },
        "collar_le3px_before": int((p & (dcat <= collar_px)).sum()),
        "collar_le3px_after": int((occ & (dcat <= collar_px)).sum()),
        "added_dots_le3px": int((added_mask & (dcat <= collar_px)).sum()),
    }


def fast_binary_dti(
    pred_bool: np.ndarray,
    truth_bool: np.ndarray,
    *,
    d_truth: np.ndarray | None = None,
    radius: float = 3.0,
    alpha: float = 0.2,
    beta: float = 0.8,
) -> dict[str, float]:
    """Exact DTI components for unit-mass binary dot fields via Euclidean EDT."""
    p = np.asarray(pred_bool, dtype=bool)
    g = np.asarray(truth_bool, dtype=bool)
    S = float(p.sum())
    G = float(g.sum())
    if S == 0.0 or G == 0.0:
        den = alpha * S + beta * G
        return {"T": 0.0, "S": S, "M": 0.0, "G": G, "dti": 0.0 if den <= 0 else 0.0}
    d_pred = ndi.distance_transform_edt(~p)
    if d_truth is None:
        d_truth = ndi.distance_transform_edt(~g)
    T = float(np.clip(1.0 - d_pred[g] / radius, 0.0, 1.0).sum())
    M = float(np.clip(1.0 - d_truth[p] / radius, 0.0, 1.0).sum())
    den = alpha * T + alpha * (S - M) + beta * G
    score = 0.0 if den <= 0.0 else T / den
    return {"T": T, "S": S, "M": M, "G": G, "dti": score}
