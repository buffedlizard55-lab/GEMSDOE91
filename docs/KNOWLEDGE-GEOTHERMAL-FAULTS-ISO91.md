# Knowledge base: geothermal fault discovery for the GEMS Prize (session bacc7c26, 2026-10-25)

This file holds facts from official or primary sources only. Each line names its source, and every URL was
opened this session. Inferences are marked **(inference)**.

## A. The competition (DrivenData #306, DOE Office of Geothermal, NLR)

Source: https://www.drivendata.org/competitions/306/competition-doe-gems/ and `/page/967/`.

**Goal**
- Predict faults that are **not** in the public USGS database, inside the GeoDAWN region of NW Nevada and NE California.
- Test labels are new faults identified by fault experts. The region is chunked into **public** (leaderboard) and **private** test sets.

**Prize rounds**
- **Initial Prize Round:** top 5 on the private test set, $10,000 each.
- **Final Prize Round:** an expanded label set built by expert review of **all submissions**: $100k, $70k, $40k, $25k and $15k.
- The **same submission** is scored in both rounds.
- Deadline: **Dec 3, 2026, 11:59 p.m. UTC**.

**Data**
- `training_features.tif`: 19 bands at 100 m, EPSG:32611. Magnetics (anomaly, RTP, TMI and its gradients, tilt),
  geodetic strain (2nd invariant, shear, dilatation), isostatic gravity (anomaly, slope, gradients), detrended
  elevation and slope, depth to basement, conductivity, and earthquake distance and intensity.
- `existing_faults.tif`: the USGS Quaternary faults plus INGENIOUS labels.
- `1m_DEM_links.csv`: links to USGS 1 m DEM tiles.

**Rules**
- External data is allowed with a licence permitting use and sharing with the sponsor.
- The full rules are hosted on HeroX: https://www.herox.com/GEMSPrize/resource/2274.

**Metric**
- Distance-tolerant intersection (DTI) with α = 0.2, β = 0.8 and a triangular kernel of R = 300 m.
- TPw = Σ_g max p·k, FPw = Σ p(1 − max k), FNw = Σ_g (1 − max p·k).
- The published worked example gives TP 3.00, FP 1.89, FN 2.00 → 0.60.

**Submission format**
- EPSG:32611, 100 m, the same bounds as the sample, a single float32 band, values in [0, 1].
- Areas outside the bounds are null or NaN.
- This repository ships an all-finite zeros encoding (0 outside the footprint, no nodata tag), which removes the
  "Predicted values must be in range [0, 1]" error caused by sentinels.

**Reference solution:** https://github.com/drivendataorg/gems-prize-reference-solution. It is a U-Net notebook by
Prof. John Lipor, commit aebe92f dated 2026-06-16. The repo team's README notes that it uses Tversky loss (0.2/0.8).

## B. Where geothermal fluids meet faults: favourable structural settings

**Faulds & Hinz Great Basin inventory.** Sources: GDR submissions 355 and 383
(https://gdr.openei.org/submissions/355, https://gdr.openei.org/submissions/383), OSTI dataset 1148722, and
WGC 2015 / Stanford workshop papers on https://pangea.stanford.edu.

- Of ~250 catalogued Great Basin geothermal fields, **step-overs/relay ramps host ~32%**.
  **Fault terminations** (horse-tailing splays) host 25% and **fault intersections** 22%.
- Accommodation zones host 9%, displacement-transfer zones 5%, pull-aparts 3%, fault bends 2%,
  and **major range-front faults only ~1%**.
- **Quaternary faults typically lie within or near most systems.**
- The highest-temperature systems cluster in the transtensional NW Great Basin, next to the Walker Lane dextral shear zone.
- **(inference)** These settings are networks of *short, closely spaced, linking* faults (splays, relay breaches,
  intersections), not single long range fronts. Such networks are hard to map at 1:250k and are exactly the
  kind of structure an expert adds when re-mapping. That motivated ISO91 (isolated short faults as analogues).
  ISO91 tested negative on the 19-band stack (`docs/REVIEW-ISO91-BACC7C26-20261025.md`).

**Step-over statistics.** Source: Giddens et al., Stanford Geothermal Workshop 2025, https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2025/Giddens.pdf.

- More than 450 step-overs were identified across the region.
- In the western Great Basin they mostly strike N–NNE, and the mean relay-ramp width is 2.5 km.
- **(inference)** Faults linking two overlapping strands 1–3 km apart would appear as short oblique segments between mapped traces.

## C. Play fairway analysis and INGENIOUS

Sources: https://gbcge.org/current-projects/ingenious/, https://catalog.data.gov/dataset/ingenious-great-basin-regional-dataset-compilation,
and the DOE Nevada Play Fairway report (https://www.osti.gov/servlets/purl/1724080).

**Nevada Play Fairway.** It combined nine parameters into a fairway score:

1. structural setting;
2. age of recent faulting;
3. slip rates;
4. geodetic strain;
5. slip and dilation tendency;
6. earthquake density;
7. gravity;
8. temperature gradient;
9. spring and well geochemistry.

**INGENIOUS**
- Funded by DOE award DE-EE0009254, 2021–2025.
- It extends play fairway analysis to the whole Great Basin region with ~15 regional datasets: 2 m temperature probes,
  Quaternary faults, geodetic models, heat flow, magnetotellurics, magnetics, gravity, paleo-geothermal deposits,
  seismicity, spring and well chemistry, and slip and dilation tendency.
- It identified more than 1,000 favourable structural settings.
- **(inference)** Several sponsor bands (strain, gravity, earthquakes, conductivity) are play-fairway parameters.
  They describe *regions* where faults matter, not the 300 m position of a trace. That fits the poor single-feature
  canary AUCs (≤ 0.62) measured here.

## D. High-resolution topography (the main untested information source)

Source: https://www.usgs.gov/3d-elevation-program/about-3dep-products-services.

- **"All 3DEP products are available, free of charge and without use restrictions."**
- Products include lidar point clouds, 1 m DEMs and 1/3 arc-second (~10 m) DEMs, delivered through The National Map.
- **Not reachable from this sandbox.** `prd-tnm.s3.amazonaws.com` and `tnmaccess.nationalmap.gov` both failed the TLS handshake (curl exit 35) on 2026-10-25.
- **(inference)** R0's ancestor used 1 m/10 m openness and local relief and is the best live file in the fleet.
  The 100 m B12/B19 bands cannot resolve piedmont scarps under 2 m high.
  The biggest available gain is sub-100 m scarp morphometry, tested with the same gates.

## E. What the live board says about the hidden labels (MODEL, from USER-REPORTED scores)

- The public truth is ≈ 12,500 px: the uniform-lattice route and the R0 deletion chain agree.
- R0 covers ≈ 40% of it.
- New faults are depleted within 2 px of mapped faults: deleted collar dots carried ≈ 0 credit.
- The best live file puts 70% of its dots more than 1 km from the catalogue.
- Details: `docs/REVIEW-ISO91-BACC7C26-20261025.md` §1–2.
