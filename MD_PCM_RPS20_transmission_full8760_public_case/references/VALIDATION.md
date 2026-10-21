# Validation record

Validated on 2026-10-19 (America/New_York) with Gurobi 13.0.0.

## What passed

- The 8760-hour, four-zone GTEP stage reached `OPTIMAL` with objective
  2,396,599,492.17 USD, zero load shedding, and zero RPS slack.
- The strict physical-realization audit passed for 271 existing generators,
  12 generation candidates, 4 storage candidates, 838 branches, and 656 buses.
- The detailed network has one connected component containing every planning
  zone and the external boundary.
- A bounded end-to-end validation retained the annual GTEP solve and ran the
  complete 656-bus PCM formulation for all 744 hours of July. PCM reached
  `OPTIMAL` with objective 201,932,586.63 USD, zero load shedding, zero RPS
  slack, and all acceptance checks passing.

The July run exercises nodal angle-based DCOPF, unit commitment, REG-UP,
REG-DOWN, SPIN, NSPIN, storage chronology, the local 20% RPS, transferred new
generation and storage, source-case immutability, and strict physical mapping.
It is a functional integration validation, not an annual operating result.

## Demonstrated workflow

1. GTEP reads 8760 chronological hours at four Maryland planning zones plus
   `EXT` and selects annual investments.
2. The physical-realization contract maps every selected candidate to a
   predefined PCM bus. HOPE writes realized generator, storage, and branch
   tables under `output_holistic/realized_inputs/` without changing either
   source case.
3. PCM reads July's 744 chronological hours on 656 buses and 838 branches and
   operates the transferred system with unit commitment, DC power flow,
   reserves, storage chronology, and the local RPS.
4. Machine-readable reconciliation and acceptance tables compare the planning
   outputs, realized PCM inputs, and operating results.

### Annual GTEP decisions transferred to PCM

| Zone | New NGCC (MW) | New solar (MW) | Battery power (MW) | Battery energy (MWh) |
| --- | ---: | ---: | ---: | ---: |
| APS_MD | 1,341.6 | 3,557.7 | 1,399.7 | 5,598.9 |
| BGE | 2,666.9 | 3,085.7 | 1,400.0 | 5,599.9 |
| DPL_MD | 0.0 | 1,660.5 | 1,347.7 | 5,390.8 |
| PEPCO | 5,000.0 | 2,586.2 | 668.4 | 2,673.6 |
| **Total** | **9,008.5** | **10,890.1** | **4,815.8** | **19,263.2** |

Seven generation candidates and all four storage candidates were built. No
retirements or candidate transmission additions were selected in this solve.
Those transfer paths remain configured but were not exercised by this result.

### Transfer reconciliation

| Check | GTEP decision | Realized PCM input | Result |
| --- | ---: | ---: | --- |
| New generation | 19,898.519 MW | 19,898.519 MW | Pass |
| New storage power | 4,815.806 MW | 4,815.806 MW | Pass |
| New storage energy | 19,263.225 MWh | 19,263.225 MWh | Pass |
| Existing generator crosswalk | 271 assets | 271 assets | Pass |
| Candidate bus references | 16 candidates | 16 resolved | Pass |
| Source-case integrity | GTEP and PCM | unchanged | Pass |

### July PCM operating evidence

| Metric | Result |
| --- | ---: |
| PCM objective | 201,932,586.63 USD |
| Transferred new-generation dispatch | 5,864,040.3 MWh |
| Transferred storage charge | 356,810.5 MWh |
| Transferred storage discharge | 302,004.4 MWh |
| Operating reserve carried | 979,362.9 MWh |
| Maximum absolute branch flow | 4,849.1 MW |
| Load shedding | 0.0 MWh |
| RPS slack | 0.0 MWh |
| Acceptance checks | All passed |

The compact machine-readable record is
`references/july_linkage_validation_summary.csv`. The original run evidence is
under `artifacts/agent_runs/md-rps20-full8760-july-validation-v3/` in the HOPE
working tree; generated artifacts are intentionally not part of the published
input case.

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
python ModelCases/tools/md_transmission_case_related/build_md_rps20_full8760_holistic_pair.py --validation-month 7 --validation-root artifacts/agent_runs/md-rps20-july-validation
julia --project=. artifacts/agent_runs/md-rps20-july-validation/run_pair.jl
```
