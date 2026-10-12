# Maryland four-zone GTEP benchmark

This case is the aggregated planning companion to
`MD_GTEP_transmission_public_case`. Both cases are generated from the same
`MD_PCM_transmission_public_case`; this one retains the four Maryland planning
zones plus the `EXT` boundary zone instead of representing every transmission
bus as a GTEP zone.

The aggregation is explicit rather than lossy. Every generation and storage
candidate has a physical `Bus_id`. Every transmission candidate has a stable
`Corridor_ID` plus `PCM_from_bus` and `PCM_to_bus`. Therefore the direct
GTEP-to-PCM workflow can realize a zonal investment at a predetermined physical
location and audit that choice.

## Run

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_GTEP_4zone_public_case/")
```

Run the paired nodal PCM realization with:

```powershell
julia --project=. ModelCases/MD_GTEP_4zone_public_case/run_holistic_pair.jl
```

The paired PCM case uses `holistic_spatial_basis: auto`, so it inherits `zone`
from this GTEP case and `bus` from the high-resolution GTEP twin.

## Validated result

The standalone GTEP case and direct nodal PCM realization both solved to
`OPTIMAL` with HiGHS 1.13.1 and zero load shedding. The GTEP stage selected
eight generation candidates (29,021.0 MW) and four storage candidates
(6,188.4 MW / 24,753.5 MWh), with no transmission upgrade. The realization
audit confirmed that all selected zonal candidates landed at their predefined
physical buses and retained the correct PCM planning-zone labels.

## Purpose

The two Maryland GTEP cases isolate the human/computational resolution tradeoff:

- `MD_GTEP_transmission_public_case` retains 656 planning nodes and needs no
  spatial disaggregation before PCM.
- This case solves a much smaller five-zone planning problem while retaining
  predefined physical realization metadata for every candidate.

The explicit candidate locations are benchmark assumptions, not an optimal
substation-siting algorithm. Future work can replace them with alternative-site
sets or a dedicated physical-realization optimization without changing the
GTEP or PCM mathematical cores.

## Rebuild

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_gtep_4zone_twin.py
```
