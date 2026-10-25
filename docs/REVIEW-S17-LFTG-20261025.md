# Three-Pass Implementation, Physics & Governance Audit — Session 17 (`S17-LFTG`)

- **Date (UTC):** `2026-10-25`
- **Branch:** `arena/281b6ba8-gemsdoe91`
- **Preregistration:** [`docs/HYPOTHESES_S17_LFTG.md`](HYPOTHESES_S17_LFTG.md) (`sha256: 951a49b1f94b8a78f7b244d51efcb19dec86eadd449ac43feeab55e0d1806eef` — verified byte-for-byte unchanged; namespaced from `docs/HYPOTHESES_S17.md` prior to merging `origin/main` `60baa8f` to preserve concurrent `S17-CPAD` / `S17-EULR` files)
- **Research Synthesis:** [`docs/GEOTHERMAL_VENT_RESEARCH_S17_LFTG.md`](GEOTHERMAL_VENT_RESEARCH_S17_LFTG.md)
- **Machine Run Card:** [`docs/run-card-S17-LFTG.json`](run-card-S17-LFTG.json) (`verdict: "negative"`, `ok_to_download_research: true`, `ok_to_submit: false`, `slots_used: 0`)

---

## Pass 1 — Full End-to-End Implementation & Execution

1. **Autonomous Data & Registry Restoration:** Restored and SHA-256 verified all `13` licence-clean competition/external files (`sample_submission.tif`, `existing_faults.tif`, 19-band `gems-geodawn-numerical-features.tif`, GDR #1391 well/spring CSV, USGS SGMC raster, and canonical registry rasters) plus `62` `git_blob` fleet rasters (`89` unique SHA-256 rasters total).
2. **Five Ranked Geological Hypotheses Preregistered Before Coding:** Specified `H17-1` through `H17-5` in `docs/HYPOTHESES_S17_LFTG.md` (`sha256: 951a49b1...`) targeting concealed Great Basin faults lacking a `100 m` DEM scarp, and froze the file before fitting any model.
3. **20-Feature `Band 12/19`-Free Subsurface Tensor & Destriping Stack (`src/gems91/lftg17.py`):**
   - Exact spectral 3-D Laplace full-tensor gravity (`G_z`, `Gamma_zz`, Wijns `cos(theta_G)` at `200 m` & `600 m`, Cooper–Cowan hyperbolic tilt, Pedersen–Rasmussen 2-D linearity `Q_2D = 1 - |I|`, listric hanging-wall curvature asymmetry, multi-altitude `theta_G` worm persistence) using `scipy.fft.rfft2`/`irfft2` on `float32` (`complex64`, `56.96 MB` peak buffer).
   - Cardinal E–W / N–S flight-line Fourier notch destriping on `B02` (`rtp`), `B14` (`tmi`), and `B06` (`tc`) + explicit `seam_noise_ratio` confidence feature.
   - Accommodation-zone gravity dip-polarity reversal (`accomm_grav_dip_reversal`), subsurface basin-margin inflection, and deconfounded hydrothermal baffle features.
4. **Unified Label-Blind 8-km Buffered Holdout (`gems57-pooled-hide-v2`, `60,988` withheld positives):**
   - Tested all `83` active local features individually for leakage (`max symmetric AUC = 0.604400` on `b06_tc <= 0.90` — **PASS**).
   - Evaluated `CED91` (`0.062153`), `S16-PGRD` (`0.069397`), `gravity_control` (`0.074023`), reproduced `incumbent_ptha_v2` (`0.179206`), reproduced `incumbent_ptac_v2` (`0.192208`), and preregistered `S17-LFTG E1` (`0.176825`), `E2` (**`0.188596`**), and `E3` (`0.186376`) on the identical `gems57-pooled-hide-v2` split (`split_sha256 = c79f1aca…`) with 1,000 paired 20-km physical-block bootstrap draws.
   - Emitted a single freshly computed GeoTIFF `gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.tif` (`sha256: 64d589ac…`) and `.zip` (`sha256: 337010f6…`) via `vendor/gems57/submission_writer.py`.

---

## Pass 2 — Bugs, Edge Cases & Assumptions Caught and Fixed

1. **Pedersen–Rasmussen Cubic Invariant Viète Factor `2.0` (`src/gems91/lftg17.py`):**
   - *Catch:* For a trace-free symmetric $3\times 3$ Eötvös gravity gradient tensor $\boldsymbol{\Gamma}$ ($\operatorname{tr}\boldsymbol{\Gamma}=0$), Viète's depressed-cubic root formula bounds $|\det\boldsymbol{\Gamma}| \le 2(-I_1/3)^{3/2}$, requiring the factor `2.0` in $|I| = |\det\boldsymbol{\Gamma}| / [2(-I_1/3)^{3/2}] \in [0, 1]$.
   - *Fix:* Corrected denominator factor `2.0` and added unit test `test_laplace_full_tensor_step_amplitude_invariance_and_plug_rejection` verifying $Q_{2D} > 0.90$ on 2-D faults vs circular 3-D plug suppression.
2. **Main-Branch CI Regressions (`IR-91-S17-02`):**
   - *Catch:* Fast-forwarding to `origin/main` (`4f84d1b`) broke `check_artifact_policy.py` (3 unregistered `unique-offcatalogue-damagezone` files) and `pytest` (`render_geo91_portal.py` overwrote `docs/index.html` & `docs/executive-summary.html`).
   - *Fix:* Redirected `render_geo91_portal.py` to `docs/geo91.html` / `docs/geo91-executive-summary.html` and registered all missing files in `registry/artifact_policy.json` (`64` registered artifacts, `PASS`).
3. **Emitted Download Permissions (`0600` → `0644` for GitHub Pages):**
   - *Catch:* Atomic `NamedTemporaryFile` + `os.replace` left `0600` (`-rw-------`) permissions on `gems91-s17-lftg-*-zeros.{tif,zip,json}`, which can fail static serving inside GitHub Pages artifact tarballs.
   - *Fix:* Applied `os.chmod(..., 0o644)` both on disk and inside `scripts/run_s17_lftg.py`, and enforced `stat.S_IROTH` in `tests/test_s17_lftg.py`.
4. **Shared Readiness Gate Key Alignment (`canaries` vs `leakage_canary`):**
   - *Catch:* `src/gems91/readiness.py` reads `card.get("canaries")`, whereas `run_s17_lftg.py` initially wrote only `"leakage_canary"`, causing `shared_readiness_gates["canary"]` to report `False` despite all `83` canaries passing (`max_symmetric_auc = 0.6044 <= 0.90`).
   - *Fix:* Populated both `"canaries"` and `"leakage_canary"` in `scripts/run_s17_lftg.py`, `docs/run-card-S17-LFTG.json`, and `evidence/s17_lftg_20261025.json`; verified `shared_readiness_gates = {"format": True, "canary": True, "novelty": False, "assigned_lane": False, "beats_comparable_best": False, "separate_selector": False}` (`submission_ready = False`).
5. **Bootstrap RNG Alignment & Dual `>300 m` / `>500 m` Blind SGMC Standard (`IR-91-S17-01`):**
   - *Catch:* Top-level `holdout_dti.ci95` (`6`-arm call) differed by `0.002` from `holdout_dti.all_arms[winner].ci95` (`8`-arm call), and `score_blind_sgmc_suite` initially evaluated only `>500 m` (`56,822` px) rather than the shared `EH.score_off_catalogue_sgmc` `>300 m` (`62,122` px) standard.
   - *Fix:* Unified `ci95` on the single `all_arms_summary` bootstrap draw (`[0.167180, 0.210009]`) and recorded **both** `>300 m` (`62,122` px: `S17-LFTG = 0.080522` vs `S16-PGRD = 0.040384`, `R0 = 0.095386`) and `>500 m` (`56,822` px: `S17-LFTG = 0.056687`, `R0 = 0.088516`), uncovering the `300–500 m` 1:500k registration-offset & in-sample halo-crowding mechanism (`IR-91-S17-01`).
6. **Semantic HTML Attribute Hygiene (`data-submission-ready`):**
   - *Catch:* Writing literal `data-submission-ready="true"` inside prose on `docs/s17-lftg-executive-summary.html` polluted raw HTML substring scans.
   - *Fix:* Removed literal attribute text from prose and omitted `data-submission-ready` on injected callouts so every portal page has exactly one `data-submission-ready="false"` node and zero `data-submission-ready="true"` occurrences.

---

## Pass 3 — Full Verification Against All Prompt & CI Requirements

- Full `pytest` suite (`tests/test_s17_lftg.py`, `tests/test_s16_integrity.py`, `tests/test_submission_portal.py`, `tests/test_delivery_verification.py`, `tests/test_geo91.py`, etc.): **PASS**
- `scripts/check_artifact_policy.py`: **PASS** (`64` explicitly registered prediction artifacts; zero raw rasters tracked in Git)
- `scripts/verify_s16.py`, `scripts/verify_evidence.py`, `scripts/verify_current_artifact.py --with-data`, `generate_submission.py --with-data`: **PASS** (10 frozen S16 files verified byte-identical to `docs/s16/provenance.json`)
- `scripts/audit_downloads.py`: **PASS** (`64` download files audited; `gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.{tif,zip}` passes all 8 format/range/CRS/nodata/catalogue checks)
- Headless Chromium browser smoke suite (`node tools/browser/smoke.cjs`): **PASS**
- Frozen `docs/HYPOTHESES_S17_LFTG.md` SHA-256: verified `951a49b1f94b8a78f7b244d51efcb19dec86eadd449ac43feeab55e0d1806eef`
- **Pass 3 Concurrent `origin/main` (`60baa8f`, PRs #98–#114) Integration & CI Regression Repairs (`IR-91-S17-03`):**
  1. Namespaced `S17-LFTG` docs/evidence (`HYPOTHESES_S17_LFTG.md`, `GEOTHERMAL_VENT_RESEARCH_S17_LFTG.md`, `run-card-S17-LFTG.json`, `docs/s17_lftg/`, `assets/s17-lftg-support.png`, `scripts/render_s17_lftg_portal.py`, `evidence/s17_lftg_execution.log`) so `verify_s17.py --with-data` (`S17-CPAD`) and `test_s17_eulr_integrity.py` (`S17-EULR`) pass unmodified.
  2. Repaired three live `origin/main` CI breakages from PR #114 (`HEXFAR91`): restored `docs/data/run_card.json` from `evidence/run_card.json` (`test_h91_holdout_and_writer.py`, `test_mtd.py`); registered `gems91-hexfar-stagger-18-35-20261025T161307Z-d102f5f0-zeros.{tif,zip}` in `registry/artifact_policy.json` (`check_artifact_policy.py`); and reconciled `docs/olc91-index-src.html` + `docs/olc91-exec-src.html` + `render_portal.py` so `HEXFAR91`, `OLC91`, `S17-CPAD`, `S17-CDSC`, `S17-CGRD`, `S17-CWPC`, `S17-EULR`, and `S17-LFTG` all link reproducibly (`test_s16_integrity.py`, `test_submission_portal.py`, `tools/browser/smoke.cjs`).
