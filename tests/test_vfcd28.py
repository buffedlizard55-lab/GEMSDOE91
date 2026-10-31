"""Unit tests for the S28-VFCD vent/consensus feature builders (synthetic fixtures)."""
import numpy as np
import pytest

from gems91 import vfcd28 as V


CSV_HEADER = (
    "layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px,temp_c,"
    "geothermquartz_c,geothermchalc_c,geothermcat_c\n"
)


def _write_csv(tmp_path, rows):
    p = tmp_path / "gdr.csv"
    p.write_text(CSV_HEADER + "".join(rows))
    return p


def test_load_vent_cells_dedupes_and_ignores_catalogue_column(tmp_path):
    p = _write_csv(tmp_path, [
        "spring,A,Hot,10,20,0,0,999.0,78.0,209.0,,\n",   # dist_known_fault_px=999 must not matter
        "spring,A,NULL,10,20,0,0,999.0,,,,\n",            # duplicate cell, NULL class
        "well,B,Warm,30,40,0,0,1.0,50.5,,,\n",
        "well,C,Unknown,50,60,0,0,1.0,,150.0,,\n",        # geothermometer only
        "well,D,NULL,70,80,0,0,1.0,296.5,,,\n",           # very hot -> high-T by temp
        "well,E,Hot,90,90,0,0,1.0,78.0,,,\n",             # hot spring, no geothermometer -> not high-T
    ])
    cells = V.load_vent_cells(p)
    assert len(cells["rows"]) == 5  # the duplicate (10,20) record is merged
    hot = dict(zip(cells["rows"].tolist(), cells["is_hot"].tolist()))
    assert hot[10] is True and hot[30] is False
    hight = dict(zip(cells["rows"].tolist(), cells["is_hight"].tolist()))
    assert hight[10] is True   # quartz geothermometer 209 >= 150
    assert hight[50] is True   # geothermometer 150
    assert hight[70] is True   # temp 296.5
    assert hight[90] is False  # 78 C spring without geothermometer


def test_compute_vent_base_features_shapes_and_finiteness(tmp_path):
    p = _write_csv(tmp_path, [
        "s,A,Hot,5,5,0,0,0.0,78.0,,,\n",
        "s,B,Hot,5,25,0,0,0.0,120.0,,,\n",
        "s,C,Warm,45,5,0,0,0.0,40.0,,,\n",
    ])
    shape = (64, 64)
    feats, receipt = V.compute_vent_base_features(p, shape)
    assert set(feats) == set(V.VENT_BASE_NAMES)
    for name, arr in feats.items():
        assert arr.shape == shape, name
        assert np.isfinite(arr).all(), name
        assert (arr >= 0).all(), name
    assert feats["vf_hot_kernel"].max() > 0
    assert receipt["n_cells"] == 3
    assert receipt["catalogue_columns_read"] == []


def test_compute_vent_linked_features_uses_visible_only(tmp_path):
    p = _write_csv(tmp_path, ["s,A,Hot,20,20,0,0,0.0,78.0,,,\n"])
    shape = (64, 64)
    base, _ = V.compute_vent_base_features(p, shape)
    visible = np.zeros(shape, bool)
    visible[2:4, 2:4] = True
    sgmc = np.zeros(shape, bool)
    sgmc[40, :] = True
    lk = V.compute_vent_linked_features(base, p, shape, visible, sgmc)
    assert set(lk) == set(V.VENT_LINKED_NAMES)
    for name, arr in lk.items():
        assert arr.shape == shape, name
        assert np.isfinite(arr).all(), name
    # off-catalogue gate: hot kernel at (20,20) is far from visible -> preserved
    assert lk["vf_hot_kernel_offcat"][20, 20] > 0
    # a catalogue at the vent suppresses the off-cat kernel there
    visible2 = np.zeros(shape, bool)
    visible2[18:23, 18:23] = True
    lk2 = V.compute_vent_linked_features(base, p, shape, visible2, sgmc)
    assert lk2["vf_hot_kernel_offcat"][20, 20] == 0


def test_compute_consensus_features_ranks():
    shape = (32, 32)
    fp = np.ones(shape, bool)
    yy, xx = np.indices(shape)
    anc = {
        "anc_h19_5": (yy + xx).astype(np.float64),
        "anc_h19_4": (yy * 2).astype(np.float64),
        "anc_h16_1": (xx * 2).astype(np.float64),
        "anc_d1_5": np.zeros(shape),
        "anc_d2_8": np.zeros(shape),
        "anc_solo_d2_8": np.zeros(shape),
    }
    feats = V.compute_consensus_features(anc, fp)
    assert set(feats) == set(V.CONS_FEATURE_NAMES)
    cf1 = feats["cf_h195_rank"]
    assert cf1[31, 31] > cf1[0, 0]  # monotone input -> monotone rank
    assert feats["cf_anc_count_p85"].max() >= 1


def test_segment_density_counts_corridors():
    shape = (50, 50)
    rows = np.array([10, 10, 10])
    cols = np.array([5, 15, 25])
    w = np.ones(3)
    dens = V._segment_density(shape, rows, cols, w, max_len=12.0, knn=2)
    assert dens.max() > 0
    # a corridor along row 10 between the first pair should light up
    assert dens[10, 10] > 0


def test_no_cat_column_ever_parsed(tmp_path):
    """Guard: the reader must not read dist_known_fault_px even when present."""
    p = _write_csv(tmp_path, ["s,A,Hot,3,3,0,0,12345.0,78.0,,,\n"])
    cells = V.load_vent_cells(p)
    assert set(cells) == {"rows", "cols", "w_hot", "w_geot", "is_hot", "is_warm", "is_hight"}
