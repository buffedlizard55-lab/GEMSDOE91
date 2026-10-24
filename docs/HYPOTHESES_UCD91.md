# GEMSDOE91 — Session (2026-10-24) candidate hypotheses, ranked

Standing best to beat: S11-MHTR HOLDOUT-DTI 0.206406 (95% CI [0.193796,0.220176],
evaluator gems91-hide-recover-v1.0, 60,988 withheld positives) — see docs/run-card-S11.json.
Fleet best ORGANIZER-CONFIRMED cited in brief: h33-h33-2-b2 zeros = 0.2778 (GEMSDOE32);
leaderboard #1 cited = 0.4413. Neither is a HOLDOUT-DTI; never compare directly.

| Rank | ID | Layers | Physical signature | Why it should catch catalogue-missing faults | Non-fault mimic | Differs from repo | Cost |
|---|---|---|---|---|---|---|---|
| 1 | UCD-1 | Band 14 TMI, Band 2 RTP | Upward-continuation persistence: gradient magnitude at Gaussian sigma=1/3/6 px, persistence ratios g3/g1, g6/g3, DoG decay. Deep basement contacts persist/shift slowly under continuation; shallow volcanic/surficial edges decay fast | Buried range-front/basement faults under alluvium have no scarp and may be missed by USGS/INGENIOUS mapping, but their deep magnetic contact still persists at long wavelength | Shallow basalt flow margins (decay with continuation — explicitly down-weighted), flight-line seams | No prior lane used multi-scale continuation-persistence ratios of TMI; MHTR used gravity Hessian + radiometrics, worms used single-scale edges | Low (CPU, official bands only) |
| 2 | UCD-2 | UCD-1 + Band 15 depth-to-basement, Band 13 gravity | Conjunction: persistent magnetic edge where depth-to-basement gradient is high (basement step) | Fault-controlled basement steps offset the magnetic basement surface | Unfaulted basement paleo-topography / intrusive contacts | Depth-step conjunction not used as gate in prior lanes | Low |
| 3 | GEO-1 | Bands 4,7,8 geodetic strain | Strain-rate tensor localization (2nd invariant/shear maxima) | Actively straining blind faults | Measurement noise, hydrological loading; very coarse resolution | Not implemented; likely too coarse for 300 m DTI kernel | Low but low expected gain |
| 4 | RTC-1 | Band 6 radiometric TC | Structure-tensor coherence anisotropy of TC | Regolith lineaments along buried faults | Aeolian/flow-margin lineaments; partly covered by S11-MHTR TC features | Partial overlap with S11 — deprioritized | Low |
| 5 | MT-1 | Band 17 conductivity only | Conductance edge | Clay cap over blind system | Evaporite pans; needs external multi-depth MT (DOE GDR #1391, https://gdr.openei.org/submissions/1391) — obtainable but heavy; single band insufficient | Not viable without new external data — deferred | High |

Decision: test UCD-1 (E1) and UCD-2 (E2) only. Promotion gate (pre-registered):
HOLDOUT-DTI must exceed 0.206406 AND registry uniqueness PASS (surface |rho|<=0.90,
final dots <=70% within 3px) AND leakage canary PASS AND validator PASS.
Otherwise verdict = negative, TIF is research-only, NOT OK TO SUBMIT.
