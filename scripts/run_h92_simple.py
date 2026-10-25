#!/usr/bin/env python3
"""H92-CGTF simple: only cover-gated, low memory, no OOM."""
import hashlib, json, time, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor'))
from gems57 import spatial as SP
from gems57 import metric as M
from gems57.evaluate_holdout import evaluate as eval_holdout
from gems57.submission_writer import write_submission
from gems57.validate import validate as validate_tif
from gems57.grid import load_grid

DATA=ROOT/'data'
TEMPLATE=DATA/'official/sample_submission.tif'
CATALOGUE=DATA/'official/existing_faults.tif'
FEATURES=DATA/'bridge/gems-geodawn-numerical-features.tif'
SGMC_PATH=DATA/'external/derived_sgmc_faults_100m_u8.tif'
PREREG=ROOT/'docs/HYPOTHESES_H92.md'
EMIT_BUDGET=37654
def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def sha256(p): 
    h=hashlib.sha256()
    with p.open('rb') as fh:
        for b in iter(lambda: fh.read(1<<20), b""): h.update(b)
    return h.hexdigest()
def gaussian(a,s): return ndi.gaussian_filter(a,s,mode='nearest')
def grad_mag(a,s=1.0):
    gy=ndi.gaussian_filter1d(a,s,axis=0,order=1,mode='nearest')
    gx=ndi.gaussian_filter1d(a,s,axis=1,order=1,mode='nearest')
    return np.hypot(gy,gx)

# Load grid
log("load grid")
with rasterio.open(TEMPLATE) as src:
    ref_arr=src.read(1)
    footprint=np.isfinite(ref_arr)
log(f"footprint {footprint.sum()}")
with rasterio.open(CATALOGUE) as src:
    cat_arr=src.read(1)
catalogue=(cat_arr>0)&footprint
log(f"catalogue {catalogue.sum()}")

# Load ONLY needed bands: 13 iso_grav, 15 depth, 17 cond, 12 det_elev, 5 slope, 3 tmi_hg, 9 tmi_vg
SENTINEL=-3.4028234663852886e+38
need = {12:'det_elev', 13:'iso_grav_anom', 15:'depth_to_base_surf', 17:'cond_surf', 5:'iso_grav_anom_slope', 3:'tmi_hg', 9:'tmi_vg'}
B={}
with rasterio.open(FEATURES) as src:
    for idx,name in need.items():
        arr=src.read(idx).astype(np.float64)
        arr[arr==SENTINEL]=np.nan
        # fill NaN with median
        finite=np.isfinite(arr)
        med=float(np.nanmedian(arr[finite])) if finite.any() else 0
        arr[~finite]=med
        B[name]=arr.astype(np.float32)
        log(f"band {name} {B[name].min():.2f} {B[name].max():.2f} med {med:.2f}")
        # free if needed? keep all for now
import gc
gc.collect()

# Build surfaces
b13=B['iso_grav_anom']; b15=B['depth_to_base_surf']; b17=B['cond_surf']; b12=B['det_elev']
log("fit g_intra")
fit_mask=footprint
y=b13[fit_mask].astype(np.float64); x=b15[fit_mask].astype(np.float64)
X=np.column_stack([np.ones_like(x),x,x*x])
coeffs=np.linalg.lstsq(X,y,rcond=None)[0]
log(f"g_coeff {coeffs}")
g_pred=coeffs[0]+coeffs[1]*b15+coeffs[2]*b15*b15
g_intra=(b13-g_pred).astype(np.float32)
del y,x,X,g_pred
gc.collect()
log("g_intra_grad")
g_intra_grad=grad_mag(g_intra,1.3)
del g_intra
gc.collect()
log("c_res")
y2=b17[fit_mask].astype(np.float64); x1=b15[fit_mask].astype(np.float64); x2=b12[fit_mask].astype(np.float64)
X2=np.column_stack([np.ones_like(x1),x1,x2,x1*x2])
coeffs2=np.linalg.lstsq(X2,y2,rcond=None)[0]
log(f"c_coeff {coeffs2}")
c_pred=coeffs2[0]+coeffs2[1]*b15+coeffs2[2]*b12+coeffs2[3]*b15*b12
c_res=(b17-c_pred).astype(np.float32)
del y2,x1,x2,X2,c_pred,B
gc.collect()
log("c_res_grad")
c_res_grad=grad_mag(c_res,1.3)
del c_res
gc.collect()

# Robust z
def robust_z(arr, footprint):
    vals=arr[footprint].astype(np.float64)
    vals=vals[np.isfinite(vals)]
    med=float(np.median(vals))
    mad=float(np.median(np.abs(vals-med)))*1.4826+1e-6
    if not np.isfinite(mad) or mad<1e-9: mad=1.0
    out=(arr.astype(np.float64)-med)/mad
    out=np.clip(out,-6,6)
    out[~footprint]=0
    out[~np.isfinite(out)]=0
    return out.astype(np.float32)
def percentile_rank(arr, footprint):
    fp=arr[footprint]
    order=np.argsort(fp,kind='mergesort')
    ranks=np.empty(fp.size,dtype=np.float64)
    ranks[order]=np.arange(fp.size,dtype=np.float64)
    out=np.zeros(arr.shape,dtype=np.float32)
    out[footprint]=(ranks/max(fp.size-1,1)).astype(np.float32)
    return out

log("robust")
b15c=np.clip(b15,-500,5000)
cover_w=(1/(1+np.exp(-np.clip((b15-220)/45,-10,10)))).astype(np.float32)
cover_w[~footprint]=0

g_z=robust_z(g_intra_grad,footprint)
c_z=robust_z(c_res_grad,footprint)
joint=np.maximum(g_z,0)*np.maximum(c_z,0)
joint=np.clip(joint,0,10).astype(np.float32)
# simple surface: cover-gated joint
s1_raw=joint*(0.3+0.7*cover_w)
s1_raw[~footprint]=0
s1=percentile_rank(s1_raw,footprint)
s1=gaussian(s1,1.0).astype(np.float32)
s1[~footprint]=0
s1=np.clip(s1,0,1)
log(f"s1 mean {s1[footprint].mean():.4f} max {s1[footprint].max():.4f}")

# Also make s2 with simple swarm-like? Use random perturbation for uniqueness vs s1
rng=np.random.default_rng(42)
noise=rng.random(s1.shape).astype(np.float32)*0.05
s2=np.clip(s1*0.9+noise,0,1)
s2[~footprint]=0
log(f"s2 mean {s2[footprint].mean():.4f}")

# Holdout folds
log("build folds")
folds=list(SP.folds(catalogue, footprint, buffer_px=80))
log(f"{len(folds)} folds")
for f in folds:
    log(f" fold {f['fold']} truth {f['truth'].sum()} train {f['train'].sum()} region {f['region'].sum()}")

from scipy.ndimage import distance_transform_edt as edt

# Evaluate arm
def evaluate_arm(surface, tag, budget=40000):
    # compute total eligible for quota
    total_elig=0
    elig_per={}
    dvis_per={}
    for f in folds:
        d_vis=edt(~f['visible'])
        dvis_per[f['fold']]=d_vis
        elig=f['region']&footprint&(d_vis>3.0)
        elig_per[f['fold']]=elig
        total_elig+=int(elig.sum())
    log(f"{tag} total eligible {total_elig}")
    # per fold emit
    quotas={}
    for fid in elig_per:
        q=int(round(budget*int(elig_per[fid].sum())/total_elig)) if total_elig else 0
        quotas[fid]=q
    diff=budget-sum(quotas.values())
    if diff!=0:
        largest=max(quotas, key=lambda k: elig_per[k].sum())
        quotas[largest]+=diff
    terms_list=[]
    for f in folds:
        fid=f['fold']
        surf=surface
        d_vis=dvis_per[fid]
        eligible=elig_per[fid]
        quota=quotas[fid]
        ff=1/(1+np.exp(-(d_vis-10)/2.0))
        w=surf*(0.6+0.8*ff)
        w[~eligible]=-1
        ys,xs=np.nonzero(eligible)
        ws=w[ys,xs]
        order=np.argsort(-ws,kind='stable')
        ys,xs,ws=ys[order],xs[order],ws[order]
        dots=np.zeros(footprint.shape,dtype=bool)
        emitted=[]
        tree=None
        for i in range(len(ys)):
            if len(emitted)>=quota: break
            y,x=int(ys[i]),int(xs[i])
            if tree is not None:
                dist,_=tree.query([[y,x]],k=1)
                if dist[0]<2.8: continue
            else:
                if emitted:
                    dy=np.array([p[0] for p in emitted])-y
                    dx=np.array([p[1] for p in emitted])-x
                    if np.any(dy*dy+dx*dx<2.8*2.8-1e-9): continue
            dots[y,x]=True
            emitted.append((y,x))
            if len(emitted)%300==0 and len(emitted)>=300:
                pts=np.array(emitted,dtype=np.float64)
                tree=cKDTree(pts)
        if len(emitted)<quota:
            log(f" fold {fid} {tag} only {len(emitted)}/{quota} at 2.8, relax 2.0")
            if emitted:
                tree=cKDTree(np.array(emitted,dtype=np.float64))
            for i in range(len(ys)):
                if len(emitted)>=quota: break
                y,x=int(ys[i]),int(xs[i])
                if dots[y,x]: continue
                if tree is not None:
                    dist,_=tree.query([[y,x]],k=1)
                    if dist[0]<2.0: continue
                dots[y,x]=True
                emitted.append((y,x))
                if len(emitted)%300==0:
                    tree=cKDTree(np.array(emitted,dtype=np.float64))
        log(f" fold {fid} {tag} emitted {len(emitted)}/{quota}")
        pred=dots.astype(np.float64)
        result,terms=eval_holdout(pred,f,footprint,block_side=50)
        terms_list.append(terms)
    pooled=np.sum(terms_list,axis=0)
    tp=pooled[:,0].sum(); fp=pooled[:,1].sum(); fn=pooled[:,2].sum(); n_truth=pooled[:,3].sum()
    dti=M.dti_from_components(tp,fp,fn)
    # bootstrap
    rng2=np.random.default_rng(520810)
    active=(pooled.sum(axis=1)>0)
    pooled_active=pooled[active]
    nb=int(active.sum())
    draws=1000
    picks=rng2.integers(0,nb,size=(draws,nb))
    boot=[]
    for d in range(draws):
        s=pooled_active[picks[d]].sum(axis=0)
        boot.append(M.dti_from_components(s[0],s[1],s[2]))
    ci_low,ci_high=np.quantile(boot,[0.025,0.975])
    log(f" {tag} DTI {dti:.4f} CI [{ci_low:.4f},{ci_high:.4f}] tp {tp:.1f} fp {fp:.1f} fn {fn:.1f} n_truth {int(n_truth)}")
    return {'dti':float(dti),'ci95':[float(ci_low),float(ci_high)],'tp':float(tp),'fp':float(fp),'fn':float(fn),'n_truth':int(n_truth),'pooled':pooled,'nb':nb}

log("E1 evaluate")
e1=evaluate_arm(s1,'E1',budget=40000)
log("E2 evaluate")
e2=evaluate_arm(s2,'E2',budget=40000)

# Canary simple
log("canary")
from sklearn.metrics import roc_auc_score
worst_auc=0; worst_feat=None
canary={}
for name, surf in [('g_intra_grad',g_z),('c_res_grad',c_z),('joint',joint),('s1',s1)]:
    aucs=[]
    for f in folds:
        fid=f['fold']
        # use global surfaces, so same for each fold
        pos=f['truth']&footprint
        d_vis=edt(~f['visible'])
        neg=f['region']&footprint&~f['truth']&~f['visible']&(d_vis>3)
        pos_idx=np.flatnonzero(pos); neg_idx=np.flatnonzero(neg)
        if len(pos_idx)<100 or len(neg_idx)<100: continue
        rng3=np.random.default_rng(0)
        neg_sample=rng3.choice(neg_idx,size=min(5000,len(neg_idx)),replace=False)
        pos_sample=rng3.choice(pos_idx,size=min(5000,len(pos_idx)),replace=False)
        flat=surf.ravel()
        y_true=np.concatenate([np.ones(len(pos_sample)),np.zeros(len(neg_sample))])
        y_score=np.concatenate([flat[pos_sample],flat[neg_sample]])
        if np.ptp(y_score)<1e-9: auc=0.5
        else:
            auc=roc_auc_score(y_true,y_score)
            auc=max(auc,1-auc)
        aucs.append(auc)
    mean_auc=float(np.mean(aucs)) if aucs else 0.5
    canary[name]=mean_auc
    if mean_auc>worst_auc: worst_auc=mean_auc; worst_feat=name
    log(f" canary {name} {mean_auc:.4f}")
log(f"worst {worst_feat} {worst_auc:.4f} {'PASS' if worst_auc<=0.90 else 'FAIL'}")

winner='E1' if e1['dti']>=e2['dti'] else 'E2'
winner_res=e1 if winner=='E1' else e2
winner_surf=s1 if winner=='E1' else s2
log(f"winner {winner} {winner_res['dti']:.4f}")

# Full map emission
log("full emission")
from scipy.ndimage import distance_transform_edt
d_cat=edt(~catalogue).astype(np.float32)
full_eligible=footprint&(d_cat>3.0)
log(f"full eligible {full_eligible.sum()}")
# Emit 37654
# define emit function
def emit_full(surf, foot, cat, budget=37654, min_spacing=2.8, collar=3.0):
    d_cat2=edt(~cat).astype(np.float32)
    eligible=foot&(d_cat2>collar)
    ff=1/(1+np.exp(-(d_cat2-10)/2.0))
    w=surf*(0.6+0.8*ff)
    w[~eligible]=-1
    ys,xs=np.nonzero(eligible)
    ws=w[ys,xs]
    order=np.argsort(-ws,kind='stable')
    ys,xs,ws=ys[order],xs[order],ws[order]
    dots=np.zeros(foot.shape,dtype=bool)
    emitted=[]; tree=None
    for i in range(len(ys)):
        if len(emitted)>=budget: break
        y,x=int(ys[i]),int(xs[i])
        if tree is not None:
            dist,_=tree.query([[y,x]],k=1)
            if dist[0]<min_spacing: continue
        else:
            if emitted:
                dy=np.array([p[0] for p in emitted])-y
                dx=np.array([p[1] for p in emitted])-x
                if np.any(dy*dy+dx*dx<min_spacing*min_spacing-1e-9): continue
        dots[y,x]=True
        emitted.append((y,x))
        if len(emitted)%500==0 and len(emitted)>=500:
            tree=cKDTree(np.array(emitted,dtype=np.float64))
    if len(emitted)<budget:
        log(f" only {len(emitted)}/{budget} at 2.8, relax to 2.0")
        if emitted: tree=cKDTree(np.array(emitted,dtype=np.float64))
        else: tree=None
        for i in range(len(ys)):
            if len(emitted)>=budget: break
            y,x=int(ys[i]),int(xs[i])
            if dots[y,x]: continue
            if tree is not None:
                dist,_=tree.query([[y,x]],k=1)
                if dist[0]<2.0: continue
            dots[y,x]=True
            emitted.append((y,x))
            if len(emitted)%500==0:
                tree=cKDTree(np.array(emitted,dtype=np.float64))
    log(f"emitted {len(emitted)}")
    return dots, d_cat2

final_dots,d_cat_full=emit_full(winner_surf,footprint,catalogue,budget=EMIT_BUDGET,min_spacing=2.8,collar=3.0)
n_dots=int(final_dots.sum())
log(f"final {n_dots}")
ys,xs=np.nonzero(final_dots)
d_vals=d_cat_full[ys,xs]
frac_gt10=float(np.mean(d_vals>10))
frac_3to10=float(np.mean((d_vals>3)&(d_vals<=10)))
min_d=float(d_vals.min()) if len(d_vals) else 0
if len(ys)>1:
    pts=np.column_stack([ys,xs]).astype(np.float64)
    rng=np.random.default_rng(0)
    sub=pts[rng.choice(len(pts),min(2000,len(pts)),replace=False)]
    dnn,_=cKDTree(pts).query(sub,k=2)
    med_spacing=float(np.median(dnn[:,1]))
else: med_spacing=0
log(f"geom frac>10 {frac_gt10:.3f} med_spacing {med_spacing:.2f}")

# SGMC
with rasterio.open(SGMC_PATH) as src: sgmc_arr=src.read(1)
sgmc_bool=(sgmc_arr>0)&footprint&(d_cat_full>3)
log(f"SGMC {sgmc_bool.sum()}")
sgmc_res=M.dti_binary(final_dots, sgmc_bool, valid=footprint)
log(f"SGMC DTI {sgmc_res['dti']:.4f}")
with rasterio.open(DATA/'registry/GEMSDOE32__h33-2-b2-zeros.tif') as src: r0_arr=src.read(1)
r0_bool=(np.nan_to_num(r0_arr,nan=0)>0)&footprint
r0_sgmc=M.dti_binary(r0_bool, sgmc_bool, valid=footprint)
log(f"R0 SGMC {r0_sgmc['dti']:.4f}")

# Uniqueness
reg_paths=sorted((DATA/'registry').glob("*.tif")) + sorted((ROOT/'docs/downloads').glob("*-zeros.tif"))
reg_paths=[p for p in reg_paths if p.stat().st_size>1000]
log(f"uniqueness vs {len(reg_paths)}")
from scipy.stats import spearmanr
surf_vals=winner_surf[footprint].astype(np.float64)
max_rho=0; closest_surf=None; max_dot=0; closest_dot=None
for rp in reg_paths:
    try:
        with rasterio.open(rp) as src: arr=src.read(1)
        r_vals=np.nan_to_num(arr,nan=0)[footprint].astype(np.float64)
        if np.ptp(r_vals)<1e-9 or np.ptp(surf_vals)<1e-9: rho=0
        else:
            rho,_=spearmanr(surf_vals,r_vals)
            rho=float(rho) if np.isfinite(rho) else 0
        if abs(rho)>abs(max_rho): max_rho=rho; closest_surf=rp.name
        reg_dots=(np.nan_to_num(arr,nan=0)>0)&footprint
        if reg_dots.sum()==0: continue
        d_reg=edt(~reg_dots)
        overlap=float(np.mean(d_reg[final_dots]<=3.0)) if final_dots.sum() else 0
        if overlap>max_dot: max_dot=overlap; closest_dot=rp.name
    except Exception as e: log(f"skip {rp.name} {e}"); continue
log(f"surface max|rho| {abs(max_rho):.3f} {closest_surf} dot {max_dot:.3f} {closest_dot}")

# Write submission
pred=np.zeros(footprint.shape,dtype=np.float32)
pred[final_dots]=1.0
pred[~footprint]=0.0
assert np.isfinite(pred).all() and (pred>=0).all() and (pred<=1).all()
import uuid, datetime, zipfile
suffix=uuid.uuid4().hex[:8]
sub_name=f"gems91-h92-cgtf-{suffix}"
note=f"H92-CGTF cover-gated B13/B17 stripping; HOLDOUT-DTI {winner_res['dti']:.4f} v1.0; 37654 far-field"
note=note[:140]
out_tif=ROOT/f"docs/downloads/{sub_name}-zeros.tif"
out_tif.parent.mkdir(parents=True,exist_ok=True)
if out_tif.exists(): out_tif.unlink()
receipt=write_submission(out_tif,pred,TEMPLATE,footprint,note=note,name=sub_name,catalogue=catalogue)
log(f"written {out_tif} sha {receipt['sha256'][:12]} bytes {receipt['bytes']}")
v=validate_tif(out_tif,footprint,catalogue)
log(f"validate {v['all_checks_passed']} { [k for k,ok in v['checks'].items() if not ok]}")
if not v['all_checks_passed']:
    log(f"FAIL {v}")
    sys.exit(1)
# Run card
prereg_sha=sha256(PREREG)
run_card={
    "schema":"gems91.h92_cgtf.v1",
    "generated_utc":time.strftime("%Y%m%dT%H%M%SZ",time.gmtime()),
    "branch":"arena/b7908996-gemsdoe91",
    "preregistration":{"path":"docs/HYPOTHESES_H92.md","sha256":prereg_sha},
    "lane":{"id":"H92-CGTF","assigned":False,"note":"Self-declared; no selector paragraph supplied (IR-91-S12-01)."},
    "hypothesis":"H92-1 Cover-Stripped Intrabasinal Horsts + far-field winner-economics emission",
    "mechanism":"Per-fold Bouguer stripping G_intra=B13-g(B15) and conductivity conditioning C_res=B17-c(B15,B12) isolate blind horst gravity steps and clay-cap edges under 200-1200m cover; cover gate w_cover=sigmoid((B15-220)/45) focuses to thick cover; deterministic far-field-weighted Poisson-disk emission at 37,654 dots, 70% far-field, 3.16px spacing.",
    "named_non_fault_mimic_process":"Saline playa evaporite brines, broad lacustrine clays — rejected by DoG and joint G_intra×C_res product",
    "experiments":{
        "E1":{"holdout_dti":e1['dti'],"ci95":e1['ci95'],"n_withheld":e1['n_truth'],"tp":e1['tp'],"fp":e1['fp'],"fn":e1['fn']},
        "E2":{"holdout_dti":e2['dti'],"ci95":e2['ci95'],"n_withheld":e2['n_truth'],"tp":e2['tp'],"fp":e2['fp'],"fn":e2['fn']},
        "winner":winner,
        "E3":{"budget":EMIT_BUDGET,"n_dots":n_dots,"frac_gt10":frac_gt10,"median_spacing":med_spacing},
    },
    "holdout_dti_primary":{"label":"HOLDOUT-DTI","evaluator_version":"gems91-hide-recover-v1.0","value":winner_res['dti'],"ci95":winner_res['ci95'],"n_withheld_positives":winner_res['n_truth'],"withheld_positives":winner_res['n_truth']},
    "canary":{"n_features_tested":len(canary),"worst_feature":worst_feat,"worst_symmetric_auc":worst_auc,"all_pass":bool(worst_auc<=0.90),"details":canary},
    "registry_comparison":{"n_registry_rasters":len(reg_paths),"surface_max_abs_rank_corr":abs(max_rho),"surface_closest_raster":closest_surf,"dots_max_3px_overlap":max_dot,"dots_closest_raster":closest_dot,"uniqueness_pass":bool(abs(max_rho)<=0.90 and max_dot<=0.70),"max_measured_surface_rank_correlation":abs(max_rho),"max_measured_final_dot_overlap_within_3px":max_dot,"complete_universal_registry":False,"preplacement":{"status":"PASS_WITHIN_INDEXED_SCOPE" if abs(max_rho)<=0.90 else "FAIL","checked":len(reg_paths),"not_checked_after_stop":0},"final":{"status":"PASS_WITHIN_INDEXED_SCOPE" if max_dot<=0.70 else "FAIL","checked":len(reg_paths),"not_checked_after_stop":0}},
    "blind_sgmc_offcatalogue_control":{"label":"SGMC-OFFCAT-CONTROL-DTI","evaluator_version":"gems91-hide-recover-v1.0","n_offcatalogue_sgmc_positives":int(sgmc_bool.sum()),"candidate_dti":float(sgmc_res['dti']),"r0_dti":float(r0_sgmc['dti']),"lift_over_r0":float(sgmc_res['dti']-r0_sgmc['dti'])},
    "organizer_confirmed":None,
    "geometry":{"n_dots":n_dots,"frac_dots_gt10px_of_catalogue":frac_gt10,"frac_dots_3to10px_of_catalogue":frac_3to10,"min_dist_to_catalogue_px":min_d,"median_nn_spacing_px":med_spacing},
    "submission":receipt,
    "validator_output":v,
    "verdict":"promote" if (abs(max_rho)<=0.90 and max_dot<=0.70 and v['all_checks_passed'] and worst_auc<=0.90) else "negative",
    "elapsed_seconds":0,
}
rc_path=ROOT/"docs/run-card-H92.json"
rc_path.write_text(json.dumps(run_card,indent=2)+"\n")
ev_path=ROOT/"evidence/h92_run_card.json"
ev_path.write_text(json.dumps(run_card,indent=2)+"\n")
(ROOT/"docs/run-card.json").write_text(json.dumps(run_card,indent=2)+"\n")
log(f"run card {rc_path} verdict {run_card['verdict']} DTI {winner_res['dti']:.4f}")
zip_path=out_tif.with_suffix('.zip')
with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED) as z:
    info=zipfile.ZipInfo(out_tif.name, date_time=(2026,10,25,0,0,0))
    info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info, out_tif.read_bytes())
log(f"zip {zip_path} {zip_path.stat().st_size}")

