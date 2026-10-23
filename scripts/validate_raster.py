"""Format / safety gates for a candidate submission raster (agent brief section 6).

MUST-pass gates, checked against the official sample_submission.tif:

    CRS, shape, transform, dtype float32, one band, values in [0, 1],
    no NaN inside the footprint, NaN outside the footprint,
    zero mass on catalogue pixels, sha256 not already in the ledger,
    parent-diff statistics recorded, file re-read from disk after writing.

REPORT-ONLY (never a gate): catalogue hide-and-recover PROXY, leakage canary,
SGMC control. Those live in scripts/proxy.py and are deliberately absent here.

Nothing in this module writes or submits anything. It only reads and reports.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio

TOL_TRANSFORM = 1e-9


@dataclass
class Gate:
    name: str
    ok: bool
    detail: str
    must_pass: bool = True

    def line(self) -> str:
        tag = "PASS" if self.ok else ("FAIL" if self.must_pass else "INFO")
        return f"[{tag}] {self.name}: {self.detail}"


@dataclass
class Report:
    gates: list[Gate] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(g.ok for g in self.gates if g.must_pass)

    def add(self, name: str, ok: bool, detail: str, must_pass: bool = True) -> None:
        self.gates.append(Gate(name, bool(ok), detail, must_pass))

    def text(self) -> str:
        return "\n".join(g.line() for g in self.gates)


def sha256_file(path: str | Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def footprint(reference: np.ndarray) -> np.ndarray:
    """Footprint = pixels where the official reference raster is not null."""
    return np.isfinite(reference)


def _transform_close(a, b) -> bool:
    return all(abs(float(x) - float(y)) <= TOL_TRANSFORM for x, y in zip(tuple(a)[:6], tuple(b)[:6]))


def validate_raster(
    candidate: str | Path,
    reference: str | Path,
    catalogue: str | Path | None = None,
    ledger_csv: str | Path | None = None,
    parent: str | Path | None = None,
    allow_zeros_outside: bool = False,
) -> Report:
    """Run every MUST gate. Returns a Report; ``report.ok`` is the merge condition."""
    rep = Report()
    cand_p, ref_p = Path(candidate), Path(reference)

    # --- presence -----------------------------------------------------------
    if not ref_p.exists():
        rep.add("reference present", False, f"missing reference raster {ref_p} -- gates cannot run")
        return rep
    if not cand_p.exists():
        rep.add("candidate present", False, f"missing candidate raster {cand_p}")
        return rep

    # --- re-read from disk after writing ------------------------------------
    with rasterio.open(ref_p) as ref, rasterio.open(cand_p) as src:
        ref_arr = ref.read(1)
        cand = src.read(1)
        rep.add("band count == 1", src.count == 1, f"candidate bands={src.count}, reference bands={ref.count}")
        rep.add("dtype float32", src.dtypes[0] == "float32", f"candidate dtype={src.dtypes[0]}")
        rep.add("CRS matches", src.crs == ref.crs, f"candidate={src.crs} reference={ref.crs}")
        rep.add(
            "shape matches",
            src.shape == ref.shape,
            f"candidate={src.shape} reference={ref.shape}",
        )
        rep.add(
            "transform matches",
            _transform_close(src.transform, ref.transform),
            f"candidate={tuple(src.transform)[:6]} reference={tuple(ref.transform)[:6]}",
        )
        # re-read: hash the bytes on disk and compare to a fresh handle
        digest = sha256_file(cand_p)

    with rasterio.open(cand_p) as again:
        reread = again.read(1)
    rep.add(
        "re-read from disk matches in-memory band",
        np.array_equal(reread, cand, equal_nan=True),
        f"sha256={digest[:12]}",
    )

    fp = footprint(ref_arr)
    inside = cand[fp]
    outside = cand[~fp]

    finite_inside = np.isfinite(inside)
    rep.add(
        "no NaN/Inf inside footprint",
        bool(finite_inside.all()),
        f"{int((~finite_inside).sum())} non-finite of {inside.size} footprint pixels",
    )
    rep.add(
        "NaN outside footprint",
        bool(np.isnan(outside).all()) if outside.size else True,
        f"{int(np.isfinite(outside).sum())} finite of {outside.size} outside pixels"
        + ("  (<id>-zeros.tif fallback: this gate is reported as INFO by design)" if allow_zeros_outside else ""),
        must_pass=not allow_zeros_outside,
    )
    if finite_inside.any():
        v = inside[finite_inside]
        rep.add("values in [0,1]", bool(v.min() >= 0.0 and v.max() <= 1.0), f"min={v.min():.6g} max={v.max():.6g}")
        rep.add(
            "mass present",
            bool(v.sum() > 0),
            f"sum={v.sum():.1f} over {int((v > 0).sum())} positive pixels",
        )

    # --- catalogue gate -----------------------------------------------------
    if catalogue is None:
        rep.add(
            "zero catalogue mass",
            False,
            "no catalogue raster supplied -- gate UNVERIFIED (brief section 4.4)",
        )
    else:
        with rasterio.open(catalogue) as cat:
            cat_arr = cat.read(1)
        produced = np.nan_to_num(cand, nan=0.0) > 0
        on_cat = produced & (cat_arr > 0)
        n_on = int(on_cat.sum())
        mass_on = float(np.nan_to_num(cand, nan=0.0)[on_cat].sum())
        rep.add(
            "zero catalogue mass",
            n_on == 0,
            f"{n_on} positive pixels on catalogue, mass={mass_on:.3f}",
        )

    # --- ledger dedupe ------------------------------------------------------
    if ledger_csv is None:
        rep.add("sha256 not already in ledger", False, "no ledger supplied -- gate UNVERIFIED")
    else:
        seen = ledger_hashes(ledger_csv)
        rep.add(
            "sha256 not already in ledger",
            digest not in seen,
            f"sha256={digest} {'FOUND' if digest in seen else 'new'} among {len(seen)} submitted hashes",
        )

    # --- parent diff --------------------------------------------------------
    if parent is None:
        rep.add("parent-diff statistics recorded", False, "no parent raster supplied -- gate UNVERIFIED")
    else:
        pp = Path(parent)
        if not pp.exists():
            rep.add("parent-diff statistics recorded", False, f"parent raster missing: {pp}")
        else:
            with rasterio.open(pp) as par:
                parr = par.read(1)
            a = np.nan_to_num(parr, nan=0.0)
            b = np.nan_to_num(cand, nan=0.0)
            changed = ~np.isclose(a, b, atol=1e-6)
            n_changed = int(changed.sum())
            denom = int((a > 0).sum()) or 1
            rep.add(
                "parent-diff statistics recorded",
                n_changed > 0,
                f"{n_changed} pixels changed ({100.0 * n_changed / denom:.2f}% of parent dots), "
                f"parent dots={int((a > 0).sum())} child dots={int((b > 0).sum())}, "
                f"mass {a.sum():.1f} -> {b.sum():.1f}",
            )

    rep.add("sha256", True, digest)
    return rep


def ledger_hashes(ledger_csv: str | Path, statuses: tuple[str, ...] | None = ("SUBMITTED",)) -> set[str]:
    """Hashes already recorded in the ledger, from ``sha256``, ``sha256_zeros`` or ``sha8``.

    Only SUBMITTED rows count by default. A BUILT row is the bookkeeping that brief
    section 7 requires *for the file being certified*, so counting it would make the
    gate impossible to pass in the order build -> record -> certify.
    """
    import csv

    seen: set[str] = set()
    with open(ledger_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if statuses is not None:
                st = (row.get("status") or "").strip().upper()
                if st not in statuses:
                    continue
            for key in ("sha256", "sha256_zeros", "sha8"):
                val = (row.get(key) or "").strip()
                if val and val.lower() not in {"", "na", "none"}:
                    seen.add(val)
    return seen


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate a candidate raster against the sample submission.")
    ap.add_argument("candidate")
    ap.add_argument("reference", nargs="?", default="data/sample_submission.tif")
    ap.add_argument("--catalogue", default=None)
    ap.add_argument("--ledger", default="ledger/submissions.csv")
    ap.add_argument("--parent", default=None)
    ap.add_argument(
        "--allow-zeros-outside",
        action="store_true",
        help="use for the <id>-zeros.tif fallback, whose outside-footprint pixels are 0 not NaN",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rep = validate_raster(
        args.candidate,
        args.reference,
        catalogue=args.catalogue,
        ledger_csv=args.ledger,
        parent=args.parent,
        allow_zeros_outside=args.allow_zeros_outside,
    )
    if args.json:
        print(json.dumps([g.__dict__ for g in rep.gates], indent=2))
    else:
        print(rep.text())
        print("\nRESULT:", "PASS" if rep.ok else "FAIL")
    return 0 if rep.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
