"""AXIS=CONCENTRATION: move a fixed fraction of R0's dots from the lowest-prior
km-scale blocks to the highest-prior ones, holding the dot count fixed.

Mechanism card (for a structural geologist)
-------------------------------------------
Hypothesis  H1: the live score of a fixed-count dot field rises when its dots are
          redistributed toward the km-scale blocks where faults are a-priori more
          likely, even though no dot is added, moved more than a few km, or changed
          in mass.
Mechanism A dot field pays through kernel credit from nearby truth. Block-level
          prior (fault density at 5 km scale) is a far more stable signal than any
          single-pixel response, so concentrating a fixed budget of dots into
          high-prior blocks should raise T at a small cost in S (S is untouched:
          the count is identical, so (S - M) can only fall).
Mimic      A non-fault process that mimics this is *survey/coverage structure*: the
          prior itself can track flight-line density or the catalogue's own
          geometry, so "high-prior" may mean "well-surveyed" or "already mapped"
          rather than "more fault". The catalogue buffer (gate G6/G7) removes the
          direct version of this; a residual version would show up as a gain that
          does not survive on chunks far from known traces.
Prediction +0.004 to +0.020 live versus R0 (MODEL), sign positive. A change under
          0.01 is not evidence (brief 5).
Falsifier  Live delta <= 0 while the percent-changed and block-CV numbers move as
          designed => the block prior carries no transferable information at this
          scale; retire the axis rather than re-tuning the fraction.

Data requirements (all are checked by tools.preflight before this script writes
anything; a build against unpinned inputs is refused unless --allow-unpinned is
passed, which is only legitimate for the synthetic fixture):
  --parent     R0 raster (or a receipt-backed descendant), unit mass per dot
  --sample     sample_submission.tif, for CRS/transform/dtype of the output
  --catalogue  binary mask of known USGS/INGENIOUS traces (pixel-exact)
  --prior      km-scale prior raster, NOT derived from --parent's own dots
               (catalogue density on held-out blocks, Faulds interaction prior,
               or a smoothed multi-layer model), same grid as --sample

Usage:
    python -m tools.run_concentration --parent ... --sample ... --catalogue ... \
        --prior ... --parent-tag h33-h33-2-b2 --frac 0.15 --block-px 50 --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import pins, raster_io, stor  # noqa: E402

AXIS = "CONCENTRATION"


# --------------------------------------------------------------------------- #
def block_cv(dots: np.ndarray, footprint: np.ndarray, block_px: int) -> dict:
    """Coefficient of variation of dots-per-footprint-pixel across blocks."""
    nrow, ncol = footprint.shape
    nbr, nbc = -(-nrow // block_px), -(-ncol // block_px)
    fp_count = np.zeros((nbr, nbc))
    dot_count = np.zeros((nbr, nbc))
    for r, c in dots:
        dot_count[r // block_px, c // block_px] += 1
    fr, fc = np.nonzero(footprint)
    for r, c in zip(fr.tolist(), fc.tolist()):
        fp_count[r // block_px, c // block_px] += 1
    ok = fp_count > 0
    dens = dot_count[ok] / fp_count[ok]
    return {
        "block_px": block_px,
        "block_km": block_px * 0.1,
        "n_blocks_scored": int(ok.sum()),
        "mean_density": float(dens.mean()),
        "std_density": float(dens.std(ddof=0)),
        "cv": float(dens.std(ddof=0) / dens.mean()) if dens.mean() > 0 else float("nan"),
        "dot_count_per_block_p95": float(np.percentile(dot_count[ok], 95)) if ok.any() else 0.0,
    }


def block_prior(prior: np.ndarray, footprint: np.ndarray, block_px: int) -> np.ndarray:
    """Mean prior per block over footprint pixels; NaN where the block has no footprint."""
    nrow, ncol = prior.shape
    nbr, nbc = -(-nrow // block_px), -(-ncol // block_px)
    num = np.zeros((nbr, nbc))
    den = np.zeros((nbr, nbc))
    fin = np.isfinite(prior) & footprint
    rr, cc = np.nonzero(fin)
    np.add.at(num, (rr // block_px, cc // block_px), prior[rr, cc])
    np.add.at(den, (rr // block_px, cc // block_px), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, num / den, np.nan)
    # a block with < 25% of its nominal area inside the footprint is not comparable
    nominal = block_px * block_px
    coverage = den / nominal
    out[coverage < 0.25] = np.nan
    return out


# integer offsets strictly closer than 2.0 px: the 4 side neighbours and the 4
# diagonals plus the 4 knight-free distance-2 cells.  R0 has NO dot pair closer
# than 2.0 px, so honouring this set keeps the parent's own spacing rule while
# only the spatial distribution of the dots changes.
_SEP_OFFSETS = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3)
                if 0 < (dr * dr + dc * dc) <= 4.0]


def _valid_target(r: int, c: int, *, footprint, catalogue_dist, occupied: set, min_gap: float,
                  shape, min_sep: float = 0.0) -> bool:
    nrow, ncol = shape
    if not (0 <= r < nrow and 0 <= c < ncol):
        return False
    if not footprint[r, c]:
        return False
    if catalogue_dist[r, c] <= min_gap:
        return False
    if (r, c) in occupied:
        return False
    if min_sep > 0.0:
        for dr, dc in _SEP_OFFSETS:
            if (r + dr, c + dc) in occupied:
                return False
    return True


def build_concentration(
    parent: np.ndarray,
    prior: np.ndarray,
    footprint: np.ndarray,
    catalogue: np.ndarray,
    frac: float = 0.15,
    block_px: int = 50,
    low_q: float = 0.30,
    high_q: float = 0.30,
    min_gap_px: float = 3.0,
    jitter_px: int = 4,
    seed: int = 0,
    min_sep_px: float = 0.0,
    donor_exclude: np.ndarray | None = None,
) -> tuple[np.ndarray, dict]:
    """Return (new unit-mass band, statistics). Pure function; no file I/O.

    ``donor_exclude`` (bool grid, default None) quarantines parent dots on
    excluded cells: they can never be selected as donors.  Session 8 uses it
    for the IR-91-27 collar quarantine (d_cat <= 3 px dots stay in place, so a
    CONCENTRATION edit cannot silently execute a partial PRUNE - IR-91-35).
    The default preserves the GDR fleet's byte-identical behaviour exactly,
    RNG draws included: with ``donor_exclude=None`` the donor ordering and
    every downstream draw are unchanged.
    """
    if not (0.10 <= frac <= 0.20):
        raise ValueError(f"frac must be within [0.10, 0.20] per brief section 5; got {frac}")
    vals = np.nan_to_num(parent, nan=0.0)
    mask = vals > 0
    if not np.allclose(vals[mask], 1.0):
        raise ValueError("parent is not unit mass: CONCENTRATION assumes one dot = one unit")
    rng = np.random.default_rng(seed)

    dots = raster_io.dots_from_band(parent)
    before = block_cv(dots, footprint, block_px)
    bp = block_prior(prior, footprint, block_px)

    flat = bp[np.isfinite(bp)]
    if flat.size < 4:
        raise ValueError("not enough blocks with a km-scale prior inside the footprint")
    lo_thr = float(np.quantile(flat, low_q))
    hi_thr = float(np.quantile(flat, 1.0 - high_q))
    low_blocks = np.isfinite(bp) & (bp <= lo_thr)
    high_blocks = np.isfinite(bp) & (bp >= hi_thr)

    dot_block_prior = bp[dots[:, 0] // block_px, dots[:, 1] // block_px]
    is_low = low_blocks[dots[:, 0] // block_px, dots[:, 1] // block_px]
    if donor_exclude is None:
        excluded = np.zeros(len(dots), dtype=bool)
    else:
        if np.asarray(donor_exclude).shape != footprint.shape:
            raise ValueError("donor_exclude must share the grid")
        excluded = np.asarray(donor_exclude, dtype=bool)[dots[:, 0], dots[:, 1]]
    n_move = int(round(frac * len(dots)))
    donors = np.flatnonzero(is_low & ~excluded)
    if donors.size == 0:
        raise ValueError("no dots in the low-prior blocks; the parent is already concentrated")
    # lowest-prior dots first; deterministic tie-break on position
    order = np.lexsort((dots[donors, 1], dots[donors, 0], np.nan_to_num(dot_block_prior[donors], nan=-1.0)))
    donors = donors[order]
    movers = donors[: min(n_move, donors.size)]
    if movers.size < n_move:
        # the low-prior blocks are too sparse to supply the requested fraction:
        # extend into the lowest-prior dots anywhere else, never into high blocks
        rest = np.setdiff1d(np.arange(len(dots)), donors)
        rest = rest[~high_blocks[dots[rest, 0] // block_px, dots[rest, 1] // block_px] & ~excluded[rest]]
        rest_order = np.lexsort((dots[rest, 1], dots[rest, 0],
                                 np.nan_to_num(dot_block_prior[rest], nan=-1.0)))
        extra = rest[rest_order][: n_move - movers.size]
        movers = np.concatenate([movers, extra])

    catalogue_dist = ndimage.distance_transform_edt(~catalogue) if catalogue.any() else np.full(footprint.shape, np.inf)
    occ = {tuple(d) for d in dots.tolist()}
    for d in dots[movers].tolist():
        occ.discard(tuple(d))

    # donor dots inside high-prior blocks are used as anchors so the moved dots land
    # in the same local texture (clustered, not gridded)
    hi_rows = np.argwhere(high_blocks)
    hi_weights = bp[high_blocks]
    hi_weights = hi_weights / hi_weights.sum()
    hi_dot_idx = np.flatnonzero(high_blocks[dots[:, 0] // block_px, dots[:, 1] // block_px])

    placed = 0
    pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []  # (donor, target)
    for d in dots[movers].tolist():
        done = False
        for _attempt in range(200):
            if hi_dot_idx.size and rng.random() < 0.8:
                a = dots[hi_dot_idx[rng.integers(len(hi_dot_idx))]]
                r0, c0 = int(a[0]), int(a[1])
            else:
                br, bc = hi_rows[rng.choice(len(hi_rows), p=hi_weights)]
                r0 = int(br * block_px + rng.integers(block_px))
                c0 = int(bc * block_px + rng.integers(block_px))
            r = r0 + int(rng.integers(-jitter_px, jitter_px + 1))
            c = c0 + int(rng.integers(-jitter_px, jitter_px + 1))
            if _valid_target(r, c, footprint=footprint, catalogue_dist=catalogue_dist,
                             occupied=occ, min_gap=min_gap_px, shape=footprint.shape,
                             min_sep=min_sep_px):
                occ.add((r, c))
                pairs.append((tuple(d), (r, c)))
                placed += 1
                done = True
                break
        if not done:
            occ.add(tuple(d))  # cannot place: the dot stays where it was

    new_dots = np.array(sorted(occ), dtype=np.int64)
    band = raster_io.band_from_dots(footprint.shape, new_dots, footprint)
    after = block_cv(new_dots, footprint, block_px)

    # displacement of the MOVED dots only, paired donor->target (comparing the whole
    # field is meaningless when 85% of the dots never move)
    if pairs:
        pd = np.array([np.hypot(t[0] - d0[0], t[1] - d0[1]) for d0, t in pairs], float)
        moved_disp = {"n": int(len(pd)), "mean_px": float(pd.mean()),
                      "p95_px": float(np.percentile(pd, 95)), "max_px": float(pd.max())}
    else:
        moved_disp = {"n": 0, "mean_px": None, "p95_px": None, "max_px": None}
    n_changed = int(np.sum(band_from_compare(parent, band)))
    stats = {
        "axis": AXIS,
        "value": f"f{int(round(frac * 100))}-blk{block_px}",
        "frac_requested": frac,
        "frac_achieved": len(pairs) / max(1, len(dots)),
        "n_dots_parent": int(len(dots)),
        "n_dots_candidate": int(len(new_dots)),
        "count_preserved": bool(len(dots) == len(new_dots)),
        "n_dots_moved": int(len(pairs)),
        "pct_dots_moved": 100.0 * len(pairs) / max(1, len(dots)),
        "pct_px_changed_of_dots": 100.0 * n_changed / max(1, len(dots)),
        "blocks": {"low_q": low_q, "high_q": high_q, "n_low_blocks": int(low_blocks.sum()),
                   "n_high_blocks": int(high_blocks.sum())},
        "cv_before": before["cv"],
        "cv_after": after["cv"],
        "cv_target_band": [0.51, 0.59],
        "cv_detail_before": before,
        "cv_detail_after": after,
        "moved_displacement_px": moved_disp,
        "p95_displacement_px": moved_disp["p95_px"],
        "seed": seed,
        "min_gap_px": min_gap_px,
        "min_sep_px": min_sep_px,
        "jitter_px": jitter_px,
        "donor_excluded_dots": int(excluded.sum()),
        "donor_block_prior_mean": float(np.nanmean(bp[dots[movers][:, 0] // block_px, dots[movers][:, 1] // block_px])),
        "acceptor_block_prior_mean": float(np.nanmean(bp[new_dots[:, 0] // block_px, new_dots[:, 1] // block_px])),
    }
    stats["mass_outside_footprint"] = float(np.nansum(np.abs(band[~footprint])))
    stats["cv_excursion"] = bool(
        not (0.45 <= after["cv"] <= 0.70) and 0.45 <= before["cv"] <= 0.70
    )
    if stats["cv_excursion"]:
        stats["cv_warning"] = (
            f"block CV moved {before['cv']:.3f} -> {after['cv']:.3f} and left the 0.51-0.59 band "
            "reported for the best historical files. CONCENTRATION and that band pull in opposite "
            "directions; if the band is causal, cap frac at the low end (0.10)."
        )
    return band, stats


def band_from_compare(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pixels whose value changed between two unit-mass bands."""
    av = np.nan_to_num(a, nan=0.0)
    bv = np.nan_to_num(b, nan=0.0)
    return ~np.isclose(av, bv, atol=1e-7)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parent", type=Path, required=True)
    ap.add_argument("--sample", type=Path, required=True)
    ap.add_argument("--catalogue", type=Path, required=True)
    ap.add_argument("--prior", type=Path, required=True)
    ap.add_argument("--parent-tag", default="R0")
    ap.add_argument("--frac", type=float, default=0.15)
    ap.add_argument("--block-px", type=int, default=50)
    ap.add_argument("--min-gap-px", type=float, default=3.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", type=Path, default=Path("releases"))
    ap.add_argument("--dry-run", action="store_true", help="compute and report, write nothing")
    ap.add_argument("--ledger", type=Path, default=stor.LEDGER,
                    help="ledger to append to (default ledger/submissions.csv)")
    ap.add_argument("--manifest", type=Path, default=pins.MANIFEST)
    ap.add_argument("--allow-unpinned", action="store_true",
                    help="skip the manifest/sha256 preflight; ONLY for the synthetic fixture")
    ap.add_argument("--register", action="store_true",
                    help="append the ledger row (only after the gates pass; off by default so a "
                         "synthetic or scratch run cannot pollute ledger/submissions.csv)")
    args = ap.parse_args(argv)

    inputs = [args.parent, args.sample, args.catalogue, args.prior]
    if not args.allow_unpinned:
        clear, reasons = pins.check_axis(AXIS, args.manifest)
        ok_paths, results = pins.check_paths(inputs, args.manifest)
        for r in reasons + [f"{r['path']}: {r['detail']}" for r in results if not r["ok"]]:
            print(f"[BLOCKED] {r}", file=sys.stderr)
        if not (clear and ok_paths):
            print("REFUSING TO BUILD: every input must be pinned in registry/data_manifest.json "
                  "and byte-identical to its pin (brief section 4.2).", file=sys.stderr)
            return 2

    missing = [str(p) for p in (args.parent, args.sample, args.catalogue, args.prior) if not p.exists()]
    if missing:
        print("REFUSING TO BUILD. Missing inputs:\n  " + "\n  ".join(missing), file=sys.stderr)
        print("\nThis axis needs the pinned parent raster and a km-scale prior that is NOT\n"
              "derived from the parent's own dots. Register them in registry/data_manifest.json\n"
              "first (see docs/DATA.md). Nothing was written.", file=sys.stderr)
        return 2

    parent = raster_io.read_band(args.parent)
    prior = raster_io.read_band(args.prior)
    catalogue = raster_io.read_band(args.catalogue) > 0
    footprint, meta = raster_io.footprint_from_sample(args.sample)
    profile = meta["profile"]
    if "ASSUMPTION" in meta["source"]:
        print(f"WARNING: footprint {meta['source']}; pass an explicit footprint mask if the "
              "scored area is smaller than the grid", file=sys.stderr)

    band, stats = build_concentration(
        parent, prior, footprint, catalogue, frac=args.frac, block_px=args.block_px,
        min_gap_px=args.min_gap_px, seed=args.seed,
    )
    print(json.dumps(stats, indent=2))
    if args.dry_run:
        print("dry run: nothing written")
        return 0

    written = raster_io.write_named_release(
        args.out_dir, args.parent_tag, AXIS, stats["value"], band, profile, footprint
    )
    final_stem = written["stem"]

    if not args.register:
        print("not registered in the ledger (pass --register after the gates pass)")
        return 0
    row = stor.ledger_row(
        id=final_stem,
        sha256_zeros=written["sha256_zeros"],
        ranking_basis=(
            "km-scale blocks (block_px reported in notes) ranked by an EXTERNAL prior raster; "
            "the prior must not be derived from the parent's own dots"
        ), parent=args.parent_tag, axis=AXIS, value=stats["value"],
        n_dots=stats["n_dots_candidate"], pct_changed=round(stats["pct_dots_moved"], 3),
        sha256=written["sha256"], status="BUILT",
        predicted_change=stor.PREDICTED[AXIS], predicted_range="MODEL:[-0.006,+0.020]",
        notes=f"frac={args.frac} blk={args.block_px} seed={args.seed} moved={stats['n_dots_moved']} "
              f"cv={stats['cv_before']:.3f}->{stats['cv_after']:.3f} "
              f"gap>={stats['min_gap_px']}px count_fixed={stats['count_preserved']}",
    )
    stor.append_ledger(row, args.ledger)
    print(f"\nbuilt {final_stem}  sha256={written['sha256']}")
    print(f"next: python -m scripts.validate_release {written['primary']} "
          f"--catalogue data/official/existing_faults.tif --ledger ledger/submissions.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
