# Maryland 20% RPS four-zone GTEP benchmark

This standalone GTEP case is the aggregated planning stage of the Maryland
20% RPS public-data holistic benchmark. It uses four Maryland utility-planning
zones plus the `EXT` boundary zone, then realizes selected generation, storage,
retirement, and transmission decisions in the paired 656-bus PCM case.

The 20% value is a moderate benchmark policy assumption. It is not inherited
from the legacy `PJM_MD100` name and it is not intended as a policy forecast.
`clean_energy_policy: 2` requires local Maryland renewable generation without
assuming external REC trading. The case also enables system planning reserve,
GTEP spinning reserve, storage investment, and transmission-expansion options.

Every candidate has a predefined physical `Bus_id`; transmission candidates
carry stable `Corridor_ID`, `PCM_from_bus`, and `PCM_to_bus` values. These are
transparent realization assumptions rather than an optimal siting model.
`Settings/HOPE_physical_realization.yml` formalizes them as a version-1
contract. HOPE validates candidate buses, zone consistency, branch targets,
network counts, provenance, and complete source-data hashes before solving.

## Run

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_GTEP_RPS20_4zone_public_case/")
```

Run the complete GTEP-to-PCM workflow with:

```powershell
julia --project=. ModelCases/MD_GTEP_RPS20_4zone_public_case/run_holistic_pair.jl
```

The workflow hashes both source cases before and after the run, writes realized
PCM inputs and a handoff manifest under `output_holistic/`, and evaluates the
machine-readable acceptance contract in the paired PCM case.

## Validated result

The complete pair was validated with Gurobi 13.0.0. Both stages reached
`OPTIMAL`, with zero load shedding and zero RPS slack. GTEP built 29,021.0 MW
of generation and 6,188.4 MW / 24,753.5 MWh of storage. The PCM stage dispatched
1,505,670.2 MWh from transferred new generation and 108,863.4 MWh from
transferred storage. Both source input trees were unchanged, and every
machine-readable acceptance check passed.

No retirement or transmission expansion was selected in this moderate public
scenario. Those transfer paths are exercised separately by the restricted
Maryland linkage benchmark; they are not forced here by artificial costs or
ratings.
## Resolution and provenance

The GTEP view is deliberately aggregated to reflect normal planning practice.
The paired PCM case retains the public-data Maryland transmission realization.
Its topology was reconstructed from OpenStreetMap and its electrical parameters
were inferred with documented rules. It is a geographically grounded synthetic
benchmark, not an official PJM power-flow case.
