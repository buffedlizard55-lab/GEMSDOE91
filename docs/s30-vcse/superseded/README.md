# Superseded VCSE artifacts

- `gems91-s30-vcse-e3-591dots-20261031T013733Z-46c37ce3-zeros.*` — first E3
  package. The shared CELF emitter's per-reference quotas were applied against a
  58-raster halo set that included dense learning probes (e.g. `r11_greedy_mp`,
  272,853 dots, 3-px halo covering 99.87% of the candidate domain). Those
  probes are learning artifacts, not listed GEMSDOE sites or registry
  submissions; the quotas were infeasible against them and the emitter's
  post-check collapsed the raster to 591 dots. Kept for audit only.
  Fix IR-S30-05: the duplicate-gate reference set is the nine listed sites +
  `data/registry/` (44 rasters after de-dup), and the emitter reserves the
  off-quota share outside the largest halo (IR-S30-04).

The 58-ref `ref_halo_words.npy` debug dump (~98 MB) is intentionally not
committed (regenerable; large datasets stay out of Git). It can be rebuilt
from `data/fleet_registry/` + `data/registry/` with a 3 px halo dilation.
