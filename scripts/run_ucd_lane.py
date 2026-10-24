#!/usr/bin/env python3
"""UCD91 lane: upward-continuation magnetic depth-persistence (UCD-1/UCD-2).
Reuses scripts/evaluate_holdout.py, scripts/submission_writer.py, mhtr emission."""
import json, sys, time, hashlib
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts')); sys.path.insert(0,str(ROOT/'src'))
import evaluate_holdout as EH, submission_writer as SW
from gems91 import mhtr_coda as MC
DATA=ROOT/'data'; FEAT=DATA/'bridge/gems-geodawn-numerical-features.tif'
TPL=DATA/'official/sample_submission.tif'; CAT=DATA/'official/existing_faults.tif'
SGMC=DATA/'external/derived_sgmc_faults_100m_u8.tif'
BEST_PRIOR=0.206406; BUDGET=48000

def rz(a,fp):
    v=a[fp]; lo,hi=np.percentile(v,[1,99]); x=np.clip((a-lo)/(hi-lo+1e-9),0,1)
    return ((x-0.5)*4).astype(np.float32)
def grad(a,s):
    return np.hypot(ndi.gaussian_filter(a,s,order=(0,1)),ndi.gaussian_filter(a,s,order=(1,0))).astype(np.float32)

def main():
    t0=time.time()
    with rasterio.open(TPL) as s: footprint=np.isfinite(s.read(1))
    with rasterio.open(CAT) as s: cat=(s.read(1)>0)&footprint
    def band(n):
        with rasterio.open(FEAT) as s: a=s.read(n).astype(np.float32)
        a[~footprint]=np.nanmedian(a[footprint]); return a
    tmi=rz(band(14),footprint); rtp=rz(band(2),footprint)
    g1,g3,g6=grad(tmi,1),grad(tmi,3),grad(tmi,6)
    eps=1e-3
    feats=[rz(g1,footprint),rz(g3,footprint),rz(g6,footprint),
           rz(g3/(g1+eps),footprint),rz(g6/(g3+eps),footprint),
           rz((g1-g6)/(g1+eps),footprint),rz(np.abs(ndi.gaussian_filter(tmi,1)-ndi.gaussian_filter(tmi,3)),footprint),
           rz(np.abs(ndi.gaussian_filter(tmi,3)-ndi.gaussian_filter(tmi,6)),footprint),tmi,rz(tmi-rtp,footprint)]
    names=['uc_g1','uc_g3','uc_g6','uc_persist31','uc_persist63','uc_decay','uc_dog13','uc_dog36','tmi_z','tmi_minus_rtp']
    # E2 additions
    depth=rz(band(15),footprint); grav=rz(band(13),footprint)
    feats2=feats+[rz(grad(depth,2),footprint),rz(grad(grav,2),footprint),depth]
    names2=names+['depth_grad','grav_grad','depth_z']
    cache=DATA/'derived'; cache.mkdir(parents=True,exist_ok=True)
    def tomem(fl,nl,fn):
        p=cache/fn; n=int(footprint.sum())
        mm=np.memmap(p,dtype=np.float32,mode='w+',shape=(n,len(fl)));
        for j,f in enumerate(fl): mm[:,j]=f[footprint]
        mm.flush(); return np.memmap(p,dtype=np.float32,mode='r',shape=(n,len(fl))),nl
    X1,n1=tomem(feats,names,'ucd_e1.dat'); X2,n2=tomem(feats2,names2,'ucd_e2.dat')
    folds=EH.build_segment_buffered_folds(cat,footprint,bridge_px=3,buffer_px=10.0)
    print('withheld',sum(f.n_withheld for f in folds),flush=True)
    canary=EH.run_leakage_canary(X2,n2,folds,footprint,subsample_step=4)
    print('canary',canary['worst_feature'],canary['worst_symmetric_auc'],canary['all_pass'],flush=True)
    if not canary['all_pass']: raise SystemExit('CANARY FAIL')
    (ROOT/'evidence/ucd_canary.json').write_text(json.dumps(canary,indent=2))
    dcat=ndi.distance_transform_edt(~cat)
    def fit_predict(X,cols,visible,exclude,seed):
        rng=np.random.default_rng(seed); vis=visible[footprint]; exc=exclude[footprint]
        dv=ndi.distance_transform_edt(~visible)
        safe=(~vis)&(~exc)&(dv[footprint]>3.5)
        pos=np.flatnonzero(vis&(~exc)); pool=np.flatnonzero(safe)
        neg=rng.choice(pool,size=min(165000,pool.size),replace=False); neg.sort()
        idx=np.concatenate([pos,neg]); y=np.r_[np.ones(len(pos),dtype=np.int32),np.zeros(len(neg),dtype=np.int32)]
        m=HistGradientBoostingClassifier(learning_rate=0.06,max_iter=180,max_leaf_nodes=31,min_samples_leaf=75,l2_regularization=3.0,random_state=seed)
        m.fit(np.asarray(X[idx][:,cols]),y); out=np.zeros(footprint.shape,dtype=np.float32); n=int(footprint.sum()); pf=np.empty(n,dtype=np.float32)
        for s in range(0,n,450000): pf[s:min(s+450000,n)]=m.predict_proba(np.asarray(X[s:min(s+450000,n)][:,cols]))[:,1]
        out[footprint]=pf; return out
    edge=rz(g6/(g1+eps),footprint); edge=np.clip((edge+4)/8,0,1)
    pied=(depth>np.median(depth[footprint]))
    results=[]; best=None
    for ei,(X,names_,cols) in enumerate([(X1,n1,list(range(len(n1)))),(X2,n2,list(range(len(n2))))]):
        foldpred={}
        for f in folds:
            surf=fit_predict(X,cols,f.visible_faults,f.region_mask|f.withheld_faults|f.buffer_mask,seed=200+ei*10+f.fold_id)
            act=((f.region_mask|f.withheld_faults)&footprint&(~f.visible_faults)&(~f.buffer_mask))
            elig=act&(ndi.distance_transform_edt(~f.visible_faults)>3.0)
            foldpred[f.fold_id]=MC.mhtr_corridor_submodular_emit(surf,edge,pied,eligible_mask=elig,n_dots=BUDGET//4,gamma=1.22,mhtr_weight=0.45,piedmont_quota_frac=0.24,min_spacing_px=2.45)
        hr=EH.score_pooled_holdout(foldpred,folds,footprint,n_boot=200,seed=91+ei)
        print(f"E{ei+1} HOLDOUT-DTI {hr['holdout_dti']} CI {hr['ci_95']}",flush=True)
        surf=fit_predict(X,cols,cat,np.zeros_like(footprint),seed=300+ei)
        elig=footprint&(~cat)&(dcat>3.0)
        dots=MC.mhtr_corridor_submodular_emit(surf,edge,pied,eligible_mask=elig,n_dots=BUDGET,gamma=1.22,mhtr_weight=0.45,piedmont_quota_frac=0.24,min_spacing_px=2.45)
        with rasterio.open(SGMC) as s: sg=(s.read(1)>0)&footprint
        sgmc=EH.score_off_catalogue_sgmc(dots,sg,cat,footprint)
        reg=EH.default_registry_paths()
        uniq=EH.check_registry_uniqueness(surf[footprint],dots,footprint,reg)
        print(f"E{ei+1} SGMC {sgmc['dti']} uniq {uniq['uniqueness_pass']} rho {uniq['surface_max_abs_rank_corr']} ov {uniq['dots_max_3px_overlap']}",flush=True)
        rec={'exp_id':f'E{ei+1}','holdout':hr,'sgmc_offcatalogue_control':sgmc,
             'uniqueness':{'pass':uniq['uniqueness_pass'],'max_surface_abs_rank_corr':uniq['surface_max_abs_rank_corr'],'surface_closest':uniq['surface_closest_raster'],'max_3px_dot_overlap':uniq['dots_max_3px_overlap'],'dots_closest':uniq['dots_closest_raster'],'n_checked':uniq['n_registry_rasters_checked']}}
        results.append(rec)
        if best is None or hr['holdout_dti']>best[0]['holdout']['holdout_dti']: best=(rec,dots,surf)
    rec,dots,surf=best
    promote = rec['holdout']['holdout_dti']>BEST_PRIOR and rec['uniqueness']['pass']
    bundle=SW.write_validated_submission_bundle(dots,stem_prefix='gems91-ucd91',date_tag='20261024T190000Z',template_path=TPL,catalogue_path=CAT,downloads_dir=ROOT/'docs/downloads',bundle_js_filename='ucd91_submission_bundle.js')
    print('bundle',json.dumps(bundle)[:2000],flush=True)
    sha=hashlib.sha256((ROOT/'docs/downloads'/bundle['zeros_tif']).read_bytes()).hexdigest() if isinstance(bundle.get('zeros_tif'),str) and (ROOT/'docs/downloads'/bundle['zeros_tif']).exists() else bundle.get('sha256_zeros','')
    card={'schema':'gems91.run-card.v2','run_id':'UCD91-20261024','hypothesis':'UCD-1/UCD-2 upward-continuation magnetic depth-persistence (docs/HYPOTHESES_UCD91.md)',
      'mechanism':'TMI gradient persistence across Gaussian sigma 1/3/6 px (continuation proxy); E2 adds depth-to-basement step conjunction; HGB per fold on visible faults only, no catalogue-derived features; submodular 300m emission 48000 dots',
      'non_fault_mimic':'Shallow basalt flow margins and flight-line seams (down-weighted by continuation decay feature)',
      'experiments':results,'leakage_canary':{'worst_feature':canary['worst_feature'],'worst_symmetric_auc':canary['worst_symmetric_auc'],'all_pass':canary['all_pass'],'n_features':canary['n_features_tested']},
      'label_rule':'All scores HOLDOUT-DTI evaluator gems91-hide-recover-v1.0, 60988 withheld positives, alpha0.2 beta0.8 300m kernel, unless labelled SGMC-OFFCAT-CONTROL-DTI. No ORGANIZER-CONFIRMED score claimed.',
      'prior_best_holdout_dti':BEST_PRIOR,'beats_prior_best':bool(rec['holdout']['holdout_dti']>BEST_PRIOR),
      'registry_comparison':rec['uniqueness'],'raster_sha256_zeros':sha,'bundle':bundle,
      'validator_output':bundle.get('validation',bundle),'submission_name':bundle.get('candidate_id',''),'note_140':'GEMS91 UCD91: TMI upward-continuation persistence (+basement step E2), 48000d, holdout-gated, see run card'[:140],
      'verdict':'promote' if promote else 'negative','submission_ready':bool(promote),
      'ok_to_submit':bool(promote),'elapsed_s':round(time.time()-t0,1)}
    (ROOT/'docs/run-card-UCD91.json').write_text(json.dumps(card,indent=2,default=str))
    (ROOT/'evidence/ucd_run_card.json').write_text(json.dumps(card,indent=2,default=str))
    print(json.dumps({'verdict':card['verdict'],'winner':rec['exp_id'],'holdout':rec['holdout']['holdout_dti'],'sha':sha,'bundle_keys':list(bundle.keys())},default=str))
if __name__=='__main__': main()
