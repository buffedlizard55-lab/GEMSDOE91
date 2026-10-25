# Project Limitations & Next Steps

## Current Limitations & Blockers
1. **Outbound Data Access Blocking:** The full official competition datasets (e.g., `existing_faults.tif`, `training_features.tif`, `gems-geodawn-numerical-features.tif`) hosted on Dropbox or the DrivenData portal are inaccessible via `wget` or `curl` from within the current restricted sandbox environment due to proxy/firewall limits.
2. **Missing Prerequisite Tooling:** While scripts depend on `TEMPLATE_TIF` and `CATALOGUE_TIF`, no direct `.sh` download script functions autonomously within the current environment. 
3. **True Ground Truth Unavailability:** The lack of real `CATALOGUE_TIF` masks prevents true baseline scoring (HOLDOUT-DTI calculation) inside the sandbox, forcing us to use mock catalogues to satisfy validation scripts or purely synthetic data approaches.

## Next Steps for the Following Sessions
1. **Data Ingestion Proxy/Workaround:** Develop a script to ingest the actual baseline rasters (such as the 1m DEM links and `existing_faults.tif`) from a fully permissive environment or explicitly provide the `data/` volume snapshot from the user's host machine into the workspace.
2. **Implement Hypothesis 1 on Real Data:** Once real gravity and topographic rasters are placed into `data/`, we must execute the Multi-scale Edge Detection on Isostatic Residual Gravity (Hypothesis 1) to derive genuine geothermal vent predictions.
3. **Evaluate Holdout Set Effectively:** Use `evaluate_holdout.py` strictly enforcing Rule 4 (Leakage Canary) against the downloaded true features.
4. **Iterative Novelty Gates Check:** Run the generated hypotheses through `evaluate_holdout.check_registry_uniqueness()` against the 92 existing fleet submissions to ensure correlation remains below `0.90` and spatial dot overlap beneath `0.70`.
