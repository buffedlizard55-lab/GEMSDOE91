#!/usr/bin/env python3
"""F91 forensics (diagnostics only; NOT an experiment, NOT a score).

Recomputes, from the pinned bytes on disk:
  * dot counts / catalogue-distance / nearest-neighbour spacing of the
    R0 lineage (h19-5 surface -> d1.5 -> d2.8 -> solo -> R0/B2-prune);
  * subset relations between those dot sets;
  * the score-algebra inversion implied by the *owner-reported* (CLAIM)
    scores of nested pairs, under the stated assumption that the removed
    <=2 px collar dots carried ~zero hidden-truth kernel credit
    (official DTI: DTI = T / (0.2*T + 0.2*(S-M) + 0.8*|G|));
  * the directed 3-px overlap of R0 itself against the synthetic lattice
    calibrator (the literal lane rule's known failure mode, IR-CED-003);
  * R0 dot enrichment in each sponsor band (single-band symmetric AUC of
    R0 dots vs matched footprint background) -- what the ancestor detector
    was, empirically.

Every organizer number used here is labelled CLAIM (user/owner reported,
no receipt in this repo; the GEMSDOE32 site itself says the B2 file was
UNSCORED there with a 0.2747 projection). Outputs are MODEL/RECEIPT only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_holdout import fast_mann_whitney_auc  # noqa: E402
from gems91 import io as GIO  # noqa: E402

SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
REG = ROOT / "data/registry"
FLEET = ROOT / "data/fleet_registry"

# Owner/user-reported scores (CLAIM). Sources: user brief fleet table;
# GEMSDOE25/GEMSDOE32 sitesFetched 2026-10-24 (both label them unverified).
LINEAGE = {
    "h19_5_surface": (REG / "calib_h195_01922.tif", 0.1922),
    "h19_4_surface": (REG / "calib_h194_01894.tif", 0.1894),
    "h16_1_surface": (REG / "calib_h161_01855.tif", 0.1855),
    "d1_5_dotted": (REG / "calib_d15_02477.tif", 0.2477),
    "d2_8_dotted": (REG / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600),
    "solo_d2_8": (REG / "GEMSDOE28__h27-4-r1-solo-d2-8.tif", 0.2708),
    "r0_b2_prune": (REG / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif", 0.2778),
}


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        return s.read(1)


def main() -> int:
    fp = np.isfinite(read1(SAMPLE))
    cat = (read1(CAT) > 0) & fp
    dcat = ndi.distance_transform_edt(~cat)
    out: dict = {"evidence_class": "RECEIPT+MODEL diagnostics; scores CLAIM",
                 "footprint_px": int(fp.sum()), "catalogue_px": int(cat.sum()),
                 "files": {}, "subsets": {}, "inversion": {}}
    masks: dict[str, np.ndarray] = {}
    for name, (path, claim) in LINEAGE.items():
        a = read1(path)
        dots = GIO.dot_mask(a)
        masks[name] = dots
        yy, xx = np.nonzero(dots)
        nn = cKDTree(np.c_[yy, xx]).query(np.c_[yy, xx], k=2)[0][:, 1] if len(yy) > 1 else np.array([])
        vals = a[dots]
        out["files"][name] = {
            "path": str(path.relative_to(ROOT)), "sha256_RECEIPT": GIO.sha256_file(path),
            "claimed_score_CLAIM": claim, "positive_px_RECEIPT": int(dots.sum()),
            "mass_sum_RECEIPT": round(float(np.nan_to_num(a, nan=0.0).sum()), 1),
            "value_max_RECEIPT": round(float(np.nanmax(a)), 4),
            "binary_unit_mass": bool(np.all((vals == 1.0))),
            "min_dcat_px": round(float(dcat[dots].min()), 4),
            "dots_by_dcat": {f"le{k}": int((dcat[dots] <= k).sum()) for k in (1, 2, 3, 8, 15)},
            "nn_spacing_px": {"min": round(float(nn.min()), 3), "median": round(float(np.median(nn)), 3),
                              "p90": round(float(np.percentile(nn, 90)), 3)} if nn.size else None,
        }
        del a
    pairs = [("r0_b2_prune", "d2_8_dotted"), ("r0_b2_prune", "solo_d2_8"),
             ("d2_8_dotted", "h19_5_surface"), ("d1_5_dotted", "h19_5_surface"),
             ("solo_d2_8", "d2_8_dotted")]
    for child, parent in pairs:
        c, p = masks[child], masks[parent]
        out["subsets"][f"{child}_in_{parent}"] = {
            "child_px": int(c.sum()), "parent_px": int(p.sum()),
            "child_not_in_parent_px": int((c & ~p).sum()),
            "exact_subset": bool(not (c & ~p).any())}
    # Is R0 exactly "ancestor minus dots with dcat <= 2"?
    for anc in ("d2_8_dotted", "solo_d2_8"):
        rebuilt = masks[anc] & (dcat > 2.0)
        out["subsets"][f"r0_equals_{anc}_minus_dcat_le2"] = bool(np.array_equal(rebuilt, masks["r0_b2_prune"]))

    # --- score-algebra inversion on nested CLAIM pairs (MODEL) -------------
    # Removing dots with zero hidden credit (T,M of remainder unchanged)
    # reduces the denominator by alpha * n_removed.  With s = T/D:
    #   D_new = alpha*n_removed / (s_new/s_old - 1);  T = s_new * D_new.
    # Under the further near-bijection approximation T ~= M for the kept
    # set, D_new ~= alpha*S_new + beta*|G|  =>  |G| estimate.
    alpha, beta = 0.2, 0.8
    for child, parent in (("r0_b2_prune", "d2_8_dotted"), ("r0_b2_prune", "solo_d2_8")):
        s_new = LINEAGE[child][1]; s_old = LINEAGE[parent][1]
        n_removed = int(masks[parent].sum() - masks[child].sum())
        d_new = alpha * n_removed / (s_new / s_old - 1.0)
        t_est = s_new * d_new
        g_est = (d_new - alpha * int(masks[child].sum())) / beta
        out["inversion"][f"{parent}->{child}"] = {
            "assumption": "removed <=2px collar dots had zero hidden kernel credit; T,M of kept set unchanged; |G| step also assumes T~=M",
            "n_removed": n_removed, "score_old_CLAIM": s_old, "score_new_CLAIM": s_new,
            "implied_denominator_new_MODEL": round(float(d_new), 1),
            "implied_TPw_new_MODEL": round(float(t_est), 1),
            "implied_hidden_truth_px_MODEL": round(float(g_est), 0),
            "implied_credit_per_dot_MODEL": round(float(t_est / masks[child].sum()), 4),
            "marginal_bar_alpha_x_dti_MODEL": round(alpha * s_new, 4)}

    # --- literal lane rule vs the lattice calibrator (RECEIPT) -------------
    lat = GIO.dot_mask(read1(FLEET / "calib_r13lattice_00904.tif"))
    d_lat = ndi.distance_transform_edt(~lat)
    out["lattice_gate_diagnostic"] = {
        "lattice_positive_px": int(lat.sum()),
        "footprint_frac_within_3px_of_lattice": round(float((d_lat[fp] <= 3.0).mean()), 6),
        "r0_dots_within_3px_of_lattice_frac": round(float((d_lat[masks["r0_b2_prune"]] <= 3.0).mean()), 6),
        "meaning": "the literal directed rule (>70% within 3px = duplicate) rejects R0 itself "
                   "against this synthetic cover; it measures cover density, not copying. "
                   "F91 therefore reports directed overlap vs every real registry raster AND "
                   "symmetric within-3px F1, with the lattice reported separately."}
    del lat, d_lat

    # --- what was the ancestor detector? R0 enrichment per sponsor band ----
    rng = np.random.default_rng(20261024)
    r0_idx = np.flatnonzero(masks["r0_b2_prune"])
    bg_pool = np.flatnonzero(fp & ~cat & (dcat > 5.0))
    bg_idx = rng.choice(bg_pool, size=min(150_000, bg_pool.size), replace=False)
    enr = {}
    with rasterio.open(FEATS) as s:
        for b in range(1, s.count + 1):
            name = s.tags(b)["band_name"]
            a = s.read(b).astype(np.float64)
            bad = ~np.isfinite(a) | (a < -1e30)
            if bad.any():
                _, idx = ndi.distance_transform_edt(bad, return_indices=True)
                a = a[idx[0], idx[1]]
            pos = a.ravel()[r0_idx]; neg = a.ravel()[bg_idx]
            x = np.r_[pos, neg]; y = np.r_[np.ones(len(pos), bool), np.zeros(len(neg), bool)]
            auc = fast_mann_whitney_auc(x, y)
            enr[name] = {"band": b, "auc_R0_vs_background": round(float(auc), 4),
                         "symmetric": round(float(max(auc, 1 - auc)), 4)}
            del a
    out["r0_band_enrichment_MODEL"] = enr

    p = ROOT / "evidence/forensics_f91_20261024.json"
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"files": {k: (v["positive_px_RECEIPT"], v["claimed_score_CLAIM"]) for k, v in out["files"].items()},
                      "subsets": out["subsets"], "inversion": out["inversion"],
                      "lattice": out["lattice_gate_diagnostic"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
