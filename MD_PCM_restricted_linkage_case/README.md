# Maryland restricted PCM linkage benchmark

This compact 24-hour nodal PCM case is paired with
`../MD_GTEP_restricted_linkage_case`. The source inputs are immutable: GTEP decisions are
realized in memory and persisted under `output_holistic/realized_inputs/`.

The case exercises nodal angle-based DCOPF, binary unit commitment,
REG-UP/REG-DOWN/SPIN/NSPIN, demand response, RPS, storage operation, and
piecewise-linear transmission losses. See
`Settings/HOPE_holistic_acceptance.yml` for the machine-readable acceptance
contract.

Carbon-policy alternatives, resource aggregation, representative-day selection,
and interregional net interchange are intentionally outside this compact pair.

This is a deliberately stressed software benchmark, not a calibrated Maryland
production-cost study.
