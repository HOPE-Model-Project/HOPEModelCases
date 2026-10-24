# Validation record

Validated on 2026-10-23 (America/New_York) with Gurobi 13.0.0.

## What passed

- The 8760-hour, four-zone GTEP stage reached `OPTIMAL` with objective
  4,112,707,606.34 USD, zero load shedding, and zero RPS slack. Existing and
  candidate VRE used the same hourly zonal profiles later used by PCM.
- The strict physical-realization audit passed for 271 existing generators,
  12 generation candidates, 4 storage candidates, 838 branches, and 656 buses.
- The PCM-owned operational-template registry populated all four built NGCC
  rows with `Flag_UC = 1`, two-hour minimum up/down times, and a 15 USD/MW
  startup-cost assumption. The field-level provenance audit passed.
- The detailed network has one connected component containing every planning
  zone and the external boundary.
- A bounded end-to-end validation retained the annual GTEP solve and ran the
  complete 656-bus PCM formulation with 48 preceding June warm-up hours plus
  all 744 evaluation hours of July. PCM reached `OPTIMAL` with objective
  158,130,773.90 USD over the complete 792-hour solve horizon, zero load
  shedding, zero RPS slack, and all acceptance checks passing.

The July run exercises nodal angle-based DCOPF, unit commitment, REG-UP,
REG-DOWN, SPIN, NSPIN, storage chronology, the local 20% RPS, transferred new
generation and storage, operational-template realization, source-case
immutability, and strict physical mapping.
It is a functional integration validation, not an annual operating result.

## Demonstrated workflow

1. GTEP reads 8760 chronological hours at four Maryland planning zones plus
   `EXT` and selects annual investments.
2. The physical-realization contract maps every selected candidate to a
   predefined PCM bus. HOPE writes realized generator, storage, and branch
   tables under `output_holistic/realized_inputs/` without changing either
   source case.
3. PCM reads 48 preceding June warm-up hours followed by July's 744 evaluation
   hours on 656 buses and 838 branches. It operates the transferred system with
   unit commitment, DC power flow, reserves, storage chronology, and the local
   RPS. The warm-up moves the free initial-state boundary outside July.
4. Machine-readable reconciliation and acceptance tables compare the planning
   outputs, realized PCM inputs, and operating results.

### Annual GTEP decisions transferred to PCM

| Zone | New NGCC (MW) | New solar (MW) | New onshore wind (MW) | Battery power (MW) | Battery energy (MWh) |
| --- | ---: | ---: | ---: | ---: | ---: |
| APS_MD | 1,615.6 | 5,000.0 | 4,000.0 | 1,503.8 | 6,015.3 |
| BGE | 1,718.0 | 3,275.4 | 895.6 | 1,504.7 | 6,018.7 |
| DPL_MD | 1,056.5 | 1,804.3 | 553.3 | 1,501.5 | 6,005.9 |
| PEPCO | 1,592.6 | 1,806.4 | 3,076.8 | 1,501.1 | 6,004.5 |
| **Total** | **5,982.8** | **11,886.1** | **8,525.7** | **6,011.1** | **24,044.3** |

All twelve generation candidates and all four storage candidates were built. No
retirements or candidate transmission additions were selected in this solve.
Those transfer paths remain configured but were not exercised by this result.

### Transfer reconciliation

| Check | GTEP decision | Realized PCM input | Result |
| --- | ---: | ---: | --- |
| New generation | 26,394.534 MW | 26,394.534 MW | Pass |
| New storage power | 6,011.078 MW | 6,011.078 MW | Pass |
| New storage energy | 24,044.311 MWh | 24,044.311 MWh | Pass |
| Existing generator crosswalk | 271 assets | 271 assets | Pass |
| Candidate bus references | 16 candidates | 16 resolved | Pass |
| Source-case integrity | GTEP and PCM | unchanged | Pass |

### July PCM operating evidence

| Metric | Result |
| --- | ---: |
| PCM objective, including 48-hour warm-up | 158,130,773.90 USD |
| July variable generation cost | 151,027,749.62 USD |
| July transferred new-generation dispatch | 5,939,408.2 MWh |
| July storage charge | 504,986.9 MWh |
| July storage discharge | 430,991.9 MWh |
| July emissions | 1,515,662.5 tons |
| Operating reserve carried, complete horizon | 1,158,879.5 MWh |
| Maximum absolute branch flow, complete horizon | 7,371.2 MW |
| Load shedding | 0.0 MWh |
| RPS slack | 0.0 MWh |
| Acceptance checks | All passed |

The compact machine-readable record is
`references/july_linkage_validation_summary.csv`. The original run evidence is
under the agent request `md-rps20-july-346ff65a2b52456b9e9f643a7fa032f5`
in the HOPE working tree; generated artifacts are intentionally not part of the
published input case.

## Interpretation boundary

This result demonstrates a consistent and reproducible GTEP-to-PCM linkage.
It does not establish annual PCM production cost, winter reliability, seasonal
storage performance, or annual operating-policy compliance. The July PCM run
also enforces the 20% local RPS within July, which is a deliberately restrictive
integration test rather than a substitute for annual REC accounting.

## Full-year PCM resource limit

The monolithic 656-bus by 8760-hour PCM was attempted without reducing the
published inputs. Model construction exhausted memory on a 32 GB Windows
workstation at about 27.6 GB private memory and ended with
`ReadOnlyMemoryError`. Therefore, the annual PCM stage is **not claimed as
solved**. Run it on a higher-memory machine; an exact rolling-horizon workflow
would first need explicit commitment, dispatch, storage-SOC, and annual REC
state carry so that it does not change the mathematics.

## Reproduce

Validate the published inputs:

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_rps20_full8760_holistic_pair.py --validate-only
julia --project=. tools/repo_utils/audit_holistic_case_pair.jl ModelCases/MD_GTEP_RPS20_4zone_full8760_public_case ModelCases/MD_PCM_RPS20_transmission_full8760_public_case
julia --project=. tools/repo_utils/audit_pcm_network_components.jl ModelCases/MD_PCM_RPS20_transmission_full8760_public_case
```

Run the full pair on a high-memory machine:

```powershell
julia --project=. ModelCases/MD_GTEP_RPS20_4zone_full8760_public_case/run_holistic_pair.jl
```

Create the bounded July validation workspace without modifying either source
case, then run it:

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_rps20_full8760_holistic_pair.py --validation-month 7 --validation-warmup-hours 48 --validation-root artifacts/agent_runs/md-rps20-july-validation
julia --project=. artifacts/agent_runs/md-rps20-july-validation/run_pair.jl
```
