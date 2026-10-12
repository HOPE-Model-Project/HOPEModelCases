# Maryland bus-resolved GTEP benchmark

This standalone GTEP ModelCase is the planning twin of
`MD_PCM_transmission_public_case`. It uses the same 656 transmission buses, 838
physical corridors, 271 existing generators, and 168-hour July chronology. The
existing GTEP transport formulation is unchanged: each transmission bus is
represented as a GTEP zone, which preserves candidate siting and permits an
explicit, auditable handoff to nodal PCM.

## Run

From the HOPE repository root:

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_GTEP_transmission_public_case/")
```

The portable default uses HiGHS, system-level planning reserve, continuous
build fractions, and all seven source days as external representative periods
weighted to 365 days. Resource aggregation is off. Policy and operating-reserve
constraints are intentionally off so
this benchmark isolates physical realization and investment transfer.
Users with Gurobi.jl and a valid license can set `solver: gurobi`; that package
was not available in the environment used to create this case.

## Validated result

The standalone GTEP case and direct GTEP-to-PCM workflow both solved to
`OPTIMAL` with HiGHS 1.13.1 and zero load shedding. GTEP selected eight
generation candidates (28,941.2 MW) and four storage candidates (6,149.8 MW /
24,599.2 MWh). It selected no transmission upgrade in this baseline. The nodal
PCM realization also solved optimally with zero load shedding, and its audit
confirmed that all selected assets retained their explicit bus locations and
were mapped back to the correct four PCM planning zones.

To run the complete direct handoff:

```powershell
julia --project=. ModelCases/MD_GTEP_transmission_public_case/run_holistic_pair.jl
```

The direct workflow deep-copies PCM inputs, applies GTEP retirements and builds,
maps candidate `Bus_id` values back to PCM planning zones, updates nodal
`branchdata.csv` through stable `Corridor_ID` values, and writes an audit package
under the PCM holistic output directory. Neither source input folder is mutated.

## Spatial and identity design

- `holistic_spatial_basis: bus` requests bus-level pair validation; the paired
  PCM case uses `auto` and inherits this basis.
- Existing generator `Asset_ID` values equal the paired PCM `GeneratorID` values.
- Existing and candidate corridors carry `Corridor_ID` values equal to the PCM
  branch-provenance `Branch_ID` values.
- Candidate generation and storage rows include both the GTEP bus-as-zone in
  `Zone` and an explicit `Bus_id`. `Planning_Zone` is retained for auditability.
- Candidate buses are selected as the largest existing-generation bus in each
  Maryland planning zone and recorded in `references/candidate_bus_mapping.csv`.

## Candidate set

Each Maryland planning zone receives one 5,000 MW NGCC option, one 5,000 MW
solar option, one 4,000 MW onshore-wind option, and one 2,000 MW / 8,000 MWh
battery option. Four existing physical branches also receive explicitly identified
1,000 MW upgrade options. These are workflow-validation assumptions, not a
recommended Maryland expansion portfolio.

## Rebuild

The committed case is standalone. To rebuild it deterministically from the
paired PCM case:

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_gtep_nodal_twin.py
```

The builder also adds stable `Asset_ID` and `Corridor_ID` columns to the paired
PCM inputs. Structural counts and identity checks are written to
`references/build_validation.json`.

## Known limitations

- GTEP uses a transport network rather than PCM's voltage-angle DC power flow.
- Candidate siting and costs are transparent benchmark assumptions.
- Seven July days are weighted to a 365-day planning year; this is a workflow
  benchmark rather than a seasonally representative annual planning dataset.
- Public OSM network limitations and inferred ratings documented by the paired
  PCM case carry through to this case.
