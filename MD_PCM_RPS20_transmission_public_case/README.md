# Maryland 20% RPS transmission-level PCM benchmark

This standalone 656-bus PCM case is the operational stage of the Maryland 20%
RPS public-data holistic benchmark. It uses the same OpenStreetMap-derived
transmission realization as `MD_PCM_transmission_public_case` and is paired with
`MD_GTEP_RPS20_4zone_public_case`.

The case enables nodal angle-based DCOPF, unit commitment, generator and storage
chronology, REG-UP, REG-DOWN, SPIN, NSPIN, and a local Maryland 20% RPS. Reserve
requirements are 1% REG-UP, 1% REG-DOWN, 3% SPIN, and 3% NSPIN of system load.
Transmission losses remain disabled because the OSM reconstruction does not
provide validated resistance data.

The topology and ratings are transparent workflow assumptions, not an official
PJM model. See `LICENSE_DATA.md`, `references/source_data_register.csv`, and the
provenance tables for source and inference details.

## Physical-realization visualization

- `references/md_rps20_physical_realization.svg` is an offline geographic view
  of the 656 buses, 838 electrical corridors, external boundary, voltage
  evidence, planning zones, and four predefined GTEP realization sites.
- `references/md_rps20_network.geojson` provides the same buses and simplified
  endpoint-to-endpoint corridors for interactive GIS or web-map tools.

The runtime electrical network stores corridor endpoints rather than complete
OSM way geometry, so map lines are deliberately drawn as straight connections.
The visualization therefore communicates geographic grounding and mapping
assumptions without claiming to reproduce actual facility routes.
## Validated result

The end-to-end pair was validated with Gurobi 13.0.0. The 656-bus PCM unit-
commitment model reached `OPTIMAL` with zero load shedding and zero RPS slack.
It carried 233,349.7 MWh of operating reserve, dispatched 1,505,670.2 MWh from
transferred new generation, discharged 108,863.4 MWh from transferred storage,
and recorded 20,996 committed-unit hours. All acceptance checks passed and the
source GTEP and PCM inputs remained unchanged.
## Run

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_PCM_RPS20_transmission_public_case/")
```

For the linked run, execute the paired GTEP case's `run_holistic_pair.jl`.
Realized inputs, mapping audits, the handoff manifest, coverage tables, and
acceptance checks are written under this case's `output_holistic/` directory.
