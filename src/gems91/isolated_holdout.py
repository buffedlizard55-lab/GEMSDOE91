"""Live-aligned isolated-component hide-and-recover split (ISO91 instrument I1).

Repo-level SHARED extension of the pinned template. ``vendor/gems57/`` stays byte-identical to
GEMSDOE78@30f1ab94 (``registry/template_pin.json``); these two functions are proposed for upstream
adoption into ``vendor/gems57/holdout.py`` and use only template primitives (``quadrant_ids``,
``FOLD_NAMES``, ``DOMAIN_ERODE``, ``STRUCT3``). Fold dictionaries have exactly the template format
consumed by ``gems57.evaluate_holdout.evaluate``. Not a fork: no template function is copied or altered.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from gems57.holdout import DOMAIN_ERODE, FOLD_NAMES, quadrant_ids
from gems57.network import STRUCT3


def isolated_components(cat: np.ndarray, sep_px: float = 5.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Catalogue pixels whose 8-connected component has NO other component within ``sep_px``.

    Distance is Euclidean in pixels (a disk footprint of radius ``sep_px``). Returns
    ``(mask, labels, isolated_ids)``. Pure geometry of the supplied mask: callers decide
    whether that mask is the full catalogue (instrument definition) or the visible
    catalogue only (training-positive selection; ISO91).
    """
    cat = np.asarray(cat, bool)
    comp, n = ndi.label(cat, STRUCT3)
    if n == 0:
        return np.zeros(cat.shape, bool), comp, np.zeros(0, np.int64)
    r = int(np.ceil(sep_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (yy * yy + xx * xx) <= sep_px * sep_px
    hi = ndi.maximum_filter(comp, footprint=disk, mode="constant", cval=0)
    lo = ndi.minimum_filter(np.where(comp > 0, comp, n + 1), footprint=disk, mode="constant", cval=n + 1)
    touching = cat & ((hi != comp) | (lo != comp))
    bad = np.unique(comp[touching])
    ids = np.setdiff1d(np.arange(1, n + 1), bad[bad > 0], assume_unique=True)
    return np.isin(comp, ids) & cat, comp, ids


def isolated_component_draw(grid, sep_px: float = 5.0, buffer_px: int = 3,
                            boundary_px: int = DOMAIN_ERODE):
    """Live-aligned hide-and-recover split (ISO91 instrument I1, ``isolated-whole-components-loqo-v1``).

    Fold *k* withholds EVERY whole 8-connected catalogue component that (a) has no other
    catalogue component within ``sep_px`` (Euclidean) and (b) lies wholly inside the
    label-blind eroded quadrant *k*. Rationale: organiser-scored new faults are depleted next
    to the known catalogue (owner-reported collar natural experiment), whereas
    ``buffered_component_draw`` hides truth of which ~55% lies within 1 km of visible faults.

    Unlike ``buffered_component_draw`` the hidden set is PER FOLD: fold *k*'s ``visible`` /
    ``masked_known`` hide only quadrant *k*'s withheld components, so a leave-one-quadrant-out
    model for fold *k* (trained outside quadrant *k* plus a buffer) still sees the isolated
    components of the other quadrants, which are never scored in fold *k*. Visible faults stay
    pixel-exactly masked from scoring and all catalogue features must be derived from the
    fold's ``visible`` mask only. Deterministic (no seed).
    """
    if sep_px <= 0 or buffer_px < 0 or boundary_px < buffer_px:
        raise ValueError('invalid isolation/buffer parameters')
    cat = np.asarray(grid.catalogue, bool)
    quad = quadrant_ids(grid.footprint)
    iso, comp, iso_ids = isolated_components(cat, sep_px)
    folds = []
    for q, name in enumerate(FOLD_NAMES):
        region = ndi.binary_erosion(quad == q, iterations=boundary_px) if boundary_px else quad == q
        region &= grid.footprint
        candidate = np.unique(comp[iso & region])
        clipped = np.unique(comp[cat & ~region])
        eligible = np.setdiff1d(candidate[candidate > 0], clipped, assume_unique=True)
        hidden = np.isin(comp, eligible) & cat
        if not hidden.any():
            raise ValueError(f'fold {name}: no eligible isolated components')
        if (hidden & ~region).any():
            raise AssertionError('a withheld component was clipped')
        collar = ndi.distance_transform_edt(~hidden) <= buffer_px
        visible = cat & ~collar
        masked_known = cat & ~hidden
        if (visible & hidden).any() or np.any(visible & collar):
            raise AssertionError('withheld truth/context buffer reached a feature')
        minimum = float(ndi.distance_transform_edt(~visible)[hidden].min())
        if minimum <= max(buffer_px, sep_px):
            raise AssertionError('isolation/context separation was not honoured')
        receipt = dict(fold=name, held_components=int(len(eligible)),
                       withheld_positive_pixels=int(hidden.sum()), isolation_sep_px=float(sep_px),
                       boundary_buffer_px=boundary_px, feature_buffer_px=buffer_px,
                       nearest_visible_to_truth_px=minimum,
                       split_version='isolated-whole-components-loqo-v1',
                       hidden_set='per-fold', evaluation_region_label_blind=True)
        folds.append(dict(fold=q, name=name, region=region, truth=hidden & region, visible=visible,
                          masked_known=masked_known, hidden_all=hidden, receipt=receipt))
    return folds, quad
