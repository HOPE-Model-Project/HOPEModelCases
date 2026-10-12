# Maryland public-transmission PCM benchmark

This is a standalone, transmission-level Maryland PCM ModelCase for HOPE. It
uses a public-data reconstruction of the 69-765 kV network, a Maryland generator
fleet, four utility-planning zones, explicit boundary interchange capability,
and a 168-hour July chronology. It is intended for physical-realization and
GTEP-to-PCM linkage development—not as an official PJM planning model.

## Run

From the HOPE repository root:

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_PCM_transmission_public_case/")
```

Or run `julia --project=. ModelCases/MD_PCM_transmission_public_case/run_case.jl`.
The default settings use open-source HiGHS, `network_model: 2`, no unit
commitment, and no policy or reserve constraints. This isolates topology,
siting, chronology, and interchange behavior for the first validation stage.

## Validated result

The committed case was solved with HiGHS 1.13.1 across all 168 hours:

- termination status: `OPTIMAL`
- primal status: `FEASIBLE_POINT`
- load shedding: 0 MWh
- buses: 656
- branches: 838
- Maryland generators: 271 (9,331.8 MW)
- connected components: 1

Runtime output is intentionally ignored by git. Exact structural checks are in
`references/build_validation.json`.

## Case contents

- `Data_MD_PCM_transmission_public/`: complete runtime inputs; no raw OSM or
  sibling repository is needed to run the case.
- `Settings/HOPE_model_settings.yml`: standard HOPE PCM configuration.
- `references/bus_provenance.csv`: OSM element, voltage, utility territory, and
  retained component for every bus.
- `references/branch_provenance.csv`: source, base-rating rule, applied rating
  multiplier, and final case rating for every retained branch.
- `references/generator_bus_mapping.csv`: generator siting rule and mapping
  distance.
- `LICENSE_DATA.md`: data attribution and reuse notice.

## Physical-realization method

1. Download OSM substations, lines, and cables at 69, 115, 138, 230, 345, 500,
   and 765 kV within a Maryland buffer.
2. Assign Maryland buses to APS_MD, BGE, DPL_MD, or PEPCO using public utility
   service-territory polygons. Points outside those polygons become `EXT`
   boundary buses.
3. Connect line endpoints to nearby same-voltage substations and infer
   transformers inside multi-voltage substations.
4. Retain the large mainland and Eastern Shore networks and remove tiny orphan
   OSM fragments. A transparent external-PJM corridor proxy connects the two
   retained components so Maryland is not modeled as an electrical island.
5. Infer line reactance from 0.4 ohm/km on a 100 MVA base and infer base thermal
   ratings from voltage and circuit count.

OSM omits some parallel-circuit and transformer-bank detail. The runnable
benchmark therefore applies a 5× capacity multiplier to reconstructed OSM
corridors and a 25× multiplier to inferred transformer proxies. These calibrated
ratings eliminate artificial bottlenecks in the workflow-validation case; they
are scenario assumptions, not measured facility ratings. Both base rules and
applied values remain auditable in `references/branch_provenance.csv`.

## Load, generation, and interchange

- Zone peak demand and zone-specific hourly multipliers come from the existing
  PJM MD100 case. Nodal load profiles are unitless multipliers, as required by
  HOPE.
- Maryland generators come from the PJM ICARUS21 2025 base input and are mapped
  to the nearest retained substation in their source utility zone. Original
  stable IDs and source metadata are preserved.
- No authoritative Maryland boundary schedule is assumed. Flexible nodal NI has
  a 0 MW target; its positive hourly cap equals modeled system load and is
  allocated across `EXT` boundary buses in proportion to retained interface
  capacity. Imports are therefore endogenous, bounded, and physically located.

## Rebuild

The committed case is standalone. Rebuilding requires Python 3 with pandas and
the local PJM DC Health study source case:

```powershell
python tools/md_transmission_case_related/fetch_md_public_network.py
python tools/md_transmission_case_related/run_build_md_transmission_case.py
python tools/md_transmission_case_related/run_finalize_md_transmission_case.py
```

Raw downloads are ignored by git; acquisition metadata is kept in
`tools/md_transmission_case_related/references/source_fetch_manifest.json`.

## Known limitations

- OSM completeness and tagging vary by location.
- Voltage-level connectivity and generator buses are reconstructed rather than
  taken from a PJM power-flow case.
- Branch ratings, reactance, transformer links, calibration multipliers, and the
  external corridor are assumptions suitable for workflow testing and scenario
  analysis.
- Distribution networks are outside the case boundary.
- Unit commitment, reserves, policies, and transmission losses are deliberately
  deferred until this LP network baseline is accepted.
