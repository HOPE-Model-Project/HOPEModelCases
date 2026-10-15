# Gurobi validation

The complete `MD_GTEP_RPS20_4zone_public_case` to
`MD_PCM_RPS20_transmission_public_case` workflow was validated with Gurobi
13.0.0.

| Metric | Result |
| --- | ---: |
| GTEP termination | `OPTIMAL` |
| GTEP objective | $3,836,903,765.44 |
| GTEP load shedding | 0.0 MWh |
| GTEP RPS slack | 0.0 MWh |
| GTEP operating reserve | 1,183,991.0 MWh |
| New generation transferred | 29,021.0 MW |
| New storage transferred | 6,188.4 MW / 24,753.5 MWh |
| PCM termination | `OPTIMAL` |
| PCM objective | $21,307,495.71 |
| PCM load shedding | 0.0 MWh |
| PCM RPS slack | 0.0 MWh |
| PCM operating reserve | 233,349.7 MWh |
| New-generation PCM dispatch | 1,505,670.2 MWh |
| New-storage PCM discharge | 108,863.4 MWh |
| PCM committed-unit hours | 20,996 |

Every check in `Settings/HOPE_holistic_acceptance.yml` passed. Hashes taken
before and after the workflow confirmed that neither source input tree changed.

No retirement or transmission expansion was selected by this moderate public
scenario. Those transfer paths are covered by the deliberately stressed
restricted Maryland linkage benchmark rather than forced here through
unrealistic public-case costs or ratings.
