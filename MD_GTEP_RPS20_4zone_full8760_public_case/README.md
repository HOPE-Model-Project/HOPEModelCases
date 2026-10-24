# Maryland 20% RPS full-year OSM GTEP benchmark

This is the planning stage of HOPE's canonical Maryland annual GTEP-to-PCM
benchmark. It retains four Maryland planning zones plus an explicit external
boundary, uses all 8760 chronological hours, and realizes its investments in
the paired 656-bus PCM case `MD_PCM_RPS20_transmission_full8760_public_case`.

The spatial inputs, stable asset identities, candidate bus assignments, OSM
network provenance, and version-1 physical-realization contract come from the
validated 168-hour public-data benchmark. Annual normalized load, wind, and
solar profiles come from the retained Maryland full-year chronology. The RPS
target is 20% for Maryland and zero for the external boundary.

GTEP's single upward-reserve product is set to 7% of hourly load. This is the
sum of PCM's 1% REG-UP, 3% SPIN, and 3% NSPIN requirements, preventing the
planning stage from understating the upward operating capability required by
the detailed operational stage.

Each candidate references a PCM-owned `Operational_Template_ID`. The paired PCM
case defines modern NGCC, solar, wind, and four-hour battery operating
assumptions in `operational_resource_templates.csv`. Candidate-specific values
take precedence, but new thermal resources are always realized with
`Flag_UC = 1`.

`Time Period` is 1 for every row because this is full chronological mode, not
representative-day mode. Solar and wind generator rows use their zonal hourly
profiles in `gen_availability_timeseries.csv`. Dispatchable resources retain
their static `AF`, and HOPE applies `FOR` separately. No identity-compatible
annual unit-outage trace is available, so the July outage pattern from the
168-hour case is not repeated throughout the year.

Run the linked pair with:

```powershell
julia --project=. ModelCases/MD_GTEP_RPS20_4zone_full8760_public_case/run_holistic_pair.jl
```

This public-data system is a geographically grounded synthetic benchmark, not
an official PJM network model. Electrical parameters, external-boundary limits,
and candidate siting remain documented modeling assumptions.

## Validation status

The full 8760-hour GTEP stage solved to `OPTIMAL` with Gurobi, zero load
shedding, and zero RPS slack. The physical handoff and detailed PCM formulation
were then validated on all 744 hours of July; PCM also solved to `OPTIMAL` and
passed every acceptance check with zero load shedding and zero RPS slack. The
PCM solve included 48 preceding June warm-up hours so the free initial-state
boundary lies outside the July evaluation period.

The 656-bus, 8760-hour PCM case is intentionally retained at full resolution.
Its monolithic construction exceeded memory on the 32 GB validation workstation
(about 27.6 GB private memory at failure). This is a compute-resource limit, not
a successful annual PCM solve. See the paired PCM case's
`references/VALIDATION.md` for the exact scope and reproduction commands.
