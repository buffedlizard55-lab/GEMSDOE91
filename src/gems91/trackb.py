"""TRACKB: strike-consistent traces (>=1 km) chained from R0 dots.

Ranking is NOT the unrecoverable parent model ranking (IR-91-21): dots are
ranked by the transparent, label-blind S_struct used by RELIEF (lineage
corroboration + potential-field gradients, see gems91.relief). Local strike is
the principal axis of neighbouring R0 dots; a trace is a greedy chain that
never turns >35 deg and never jumps >5 px between support dots.
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import cKDTree

def local_strike(pts, radius=12.0, min_n=4):
    """pts (N,2) as (y,x). Returns (strike_deg 0-180, coherence 0-1)."""
    pts=np.asarray(pts,float); tree=cKDTree(pts)
    strike=np.full(len(pts),np.nan); coh=np.zeros(len(pts))
    for i,p in enumerate(pts):
        idx=tree.query_ball_point(p,r=radius)
        if len(idx)<min_n: continue
        c=pts[idx]-pts[idx].mean(0)
        cov=c.T@c
        w,v=np.linalg.eigh(cov)
        if w.sum()<=0: continue
        coh[i]=(w[1]-w[0])/w.sum()
        d=v[:,1]  # (dy,dx) principal axis
        strike[i]=float(np.degrees(np.arctan2(d[1],d[0]))%180.0)
    return strike, coh

def _angdiff(a,b):
    return abs((a-b+90)%180-90)

def build_traces(pts, scores, strike, coherence, *, min_length_px=10.0,
                 min_dots=4, link_px=5.0, turn_deg=35.0, min_coherence=0.35):
    pts=np.asarray(pts,float); scores=np.asarray(scores,float)
    tree=cKDTree(pts); used=np.zeros(len(pts),bool); tried=np.zeros(len(pts),bool)
    traces=[]
    order=np.argsort(-scores, kind="mergesort")
    for seed in order:
        if used[seed] or tried[seed] or not np.isfinite(strike[seed]) or coherence[seed]<min_coherence:
            continue
        tried[seed]=True
        chain=[int(seed)]
        for sign in (1,-1):
            heading=strike[seed] if sign==1 else (strike[seed]+180)%360
            cur=int(seed)
            while True:
                cand=[j for j in tree.query_ball_point(pts[cur],r=link_px)
                      if j!=cur and not used[j] and j not in chain]
                best=None
                for j in cand:
                    d=pts[j]-pts[cur]; dist=float(np.hypot(*d))
                    if dist<1.5: continue
                    ang=float(np.degrees(np.arctan2(d[1],d[0]))%360)
                    diff=abs((ang-heading+180)%360-180)
                    if diff>turn_deg: continue
                    key=(scores[j]-0.01*diff)
                    if best is None or key>best[0]: best=(key,j,ang)
                if best is None: break
                _,cur,heading=best; chain.append(cur) if sign==1 else chain.insert(0,cur)
        if len(chain)<min_dots: continue
        cp=pts[chain]
        seg=np.hypot(np.diff(cp[:,0]),np.diff(cp[:,1]))
        length=float(seg.sum())
        if length<min_length_px: continue
        used[chain]=True
        # mean strike from end-to-end vector
        v=cp[-1]-cp[0]; extent=float(np.hypot(*v))
        traces.append({
            "dot_indices": [int(x) for x in chain],
            "points_yx": cp.tolist(),
            "length_px": round(length,3), "length_km": round(length/10.0,3),
            "extent_px": round(extent,3),
            "straightness": round(extent/length,4) if length else 0.0,
            "n_dots": len(chain),
            "mean_score": round(float(scores[chain].mean()),4),
            "mean_coherence": round(float(coherence[chain].mean()),4),
            "strike_deg": round(float(np.degrees(np.arctan2(v[1],v[0]))%180.0),2),
        })
    traces.sort(key=lambda t:(-t["mean_score"], -t["length_px"]))
    for i,t in enumerate(traces,1): t["trace_id"]=f"T{i:03d}"
    return traces

def trace_sample_points(points_yx, spacing_px=3.0):
    """Interpolate a polyline at ~spacing_px; returns (M,2) float (y,x)."""
    p=np.asarray(points_yx,float)
    if len(p)<2: return p
    out=[p[0]]
    for a,b in zip(p[:-1],p[1:]):
        L=float(np.hypot(*(b-a)))
        n=max(1,int(round(L/spacing_px)))
        for k in range(1,n+1): out.append(a+(b-a)*(k/n))
    return np.array(out)
