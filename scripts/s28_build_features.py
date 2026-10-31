"""S28 feature stack: the official 19-band GEODAWN numeric feature raster.

This is the first lane in this repository that uses the *official* competition
feature stack (``gems-geodawn-numerical-features.tif``, 19 bands, sha256
``4371c82e...``) instead of hand-derived ridge formulas.

Every layer written here is a deterministic function of the 19 official bands
alone.  No catalogue, distance-to-catalogue, score or label information enters
the stack, so a leakage canary can be run on each layer independently.

Layers per band b (float32, full competition grid, NaN-free):
    z_b        robust standardisation  (x - median) / IQR   over the footprint
    s_b        Gaussian sigma = 4 px (400 m) regional context of z_b

Then three catalogue-free structural saliency products used as extra features:
    edge_mag   sqrt(mean(z_hg**2 for the three horizontal-gradient bands))
    curv       -laplacian(det_elev z), sigma = 1
    basin      z(depth_to_base_surf) * z(cond_surf)   (buried + conductive)

Output: ``data/work/s28/features.npy`` (float32, (n_layers, H, W) memmap) plus
``features.json`` with the band names, layer names and standardisation constants.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from vendor.gems57.grid import HEIGHT, WIDTH, load_grid  # noqa: E402

OFFICIAL = ROOT / "data" / "official"
FEATURES_TIF = OFFICIAL / "gems-geodawn-numerical-features.tif"
FEATURES_SHA256 = "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5"
WORK = ROOT / "data" / "work" / "s28"

NODATA = -3.4028234663852886e38


def sha256(p: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def robust_z(x: np.ndarray, fp: np.ndarray) -> tuple[np.ndarray, float, float]:
    v = x[fp]
    med = float(np.median(v))
    q1, q3 = np.percentile(v, [25, 75])
    iqr = float(q3 - q1)
    if not np.isfinite(iqr) or iqr <= 0:
        iqr = float(np.std(v)) or 1.0
    z = (x - med) / iqr
    return z.astype(np.float32), med, iqr


def smooth(a: np.ndarray, sigma: float) -> np.ndarray:
    from scipy import ndimage as ndi

    return ndi.gaussian_filter(a, sigma, mode="nearest").astype(np.float32)


def main() -> int:
    got = sha256(FEATURES_TIF)
    if got != FEATURES_SHA256:
        raise SystemExit(f"feature stack sha256 {got} != pinned {FEATURES_SHA256}")
    grid = load_grid(OFFICIAL)
    fp = grid.footprint
    with rasterio.open(FEATURES_TIF) as ds:
        desc = [ds.descriptions[i] or f"band{i + 1}" for i in range(ds.count)]
        names = [d.split(" - ")[0].strip() for d in desc]
        if ds.count != 19:
            raise SystemExit(f"expected 19 bands, got {ds.count}")

    WORK.mkdir(parents=True, exist_ok=True)
    n_layers = 2 * 19 + 3
    feats = np.lib.format.open_memmap(WORK / "features.npy", mode="w+",
                                      dtype=np.float32, shape=(n_layers, HEIGHT, WIDTH))
    stats, layer_names = {}, []
    z_cache: dict[str, np.ndarray] = {}
    with rasterio.open(FEATURES_TIF) as ds:
        for i, nm in enumerate(names, start=1):
            a = ds.read(i).astype(np.float32)
            a[~np.isfinite(a)] = np.nan
            a[a < -1e37] = np.nan
            # fill non-finite with the footprint median so every layer is finite
            med = float(np.nanmedian(a[fp]))
            a[~np.isfinite(a)] = med
            z, m, iqr = robust_z(a, fp)
            del a
            z_cache[nm] = z
            feats[2 * (i - 1)] = z
            feats[2 * (i - 1) + 1] = smooth(z, 4.0)
            layer_names += [f"z_{nm}", f"s4_{nm}"]
            stats[nm] = dict(median=m, iqr=iqr, band=i)
            print(f"band {i:2d} {nm:22s} median={m:12.4f} iqr={iqr:10.4f}", flush=True)

    hg = [z_cache[n] for n in ("tmi_hg", "iso_grav_anom_hg", "iso_grav_anom_slope")]
    edge = np.sqrt(np.mean(np.square(hg), axis=0)).astype(np.float32)
    feats[38] = edge
    layer_names.append("edge_mag_hg")

    from scipy import ndimage as ndi

    cur = (-ndi.laplace(smooth(z_cache["det_elev"], 1.0))).astype(np.float32)
    feats[39] = cur
    layer_names.append("curv_det_elev")

    feats[40] = (z_cache["depth_to_base_surf"] * z_cache["cond_surf"]).astype(np.float32)
    layer_names.append("basin_x_conductivity")

    feats.flush()
    del feats
    (WORK / "features.json").write_text(json.dumps(dict(
        schema="gems91.s28.feature-stack.v1",
        source=dict(path=str(FEATURES_TIF.relative_to(ROOT)), sha256=FEATURES_SHA256,
                    bands=names, descriptions=desc),
        standardisation="robust: (x - footprint median) / footprint IQR",
        layers=layer_names, n_layers=len(layer_names), stats=stats,
        catalogue_free=True), indent=1))
    print("layers:", len(layer_names))
    sizes = (WORK / "features.npy").stat().st_size
    print(f"features.npy {sizes / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
