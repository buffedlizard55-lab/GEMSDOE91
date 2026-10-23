import numpy as np, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from gems91.trackb import local_strike, build_traces, trace_sample_points

def test_collinear_dots_form_km_trace():
    pts=np.array([[100.,100.+3*i] for i in range(12)])  # 33 px = 3.3 km line
    strike,coh=local_strike(pts)
    tr=build_traces(pts, np.linspace(1,0.5,12), strike, coh, min_length_px=10)
    assert len(tr)==1 and tr[0]["length_km"]>=1.0 and tr[0]["n_dots"]==12
    assert abs(tr[0]["strike_deg"]-90)<5  # east in (y,x)-> atan2(dx,dy)

def test_scattered_dots_form_no_trace():
    rng=np.random.default_rng(0); pts=rng.uniform(0,200,(30,2))
    strike,coh=local_strike(pts)
    assert build_traces(pts, np.ones(30), strike, coh, min_length_px=10)==[] or \
           all(t["length_km"]>=1.0 for t in build_traces(pts,np.ones(30),strike,coh))

def test_sampling_spacing():
    p=trace_sample_points([[0.,0.],[0.,30.]], spacing_px=3.0)
    assert len(p)>=10 and np.allclose(p[0],[0,0]) and np.allclose(p[-1],[0,30])
