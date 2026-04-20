# GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8

Retained 2-day solved Germany nodal validation case derived from `GERMANY_PCM_nodal_case`.

Current role:
- bundled Germany dashboard demo case
- fast winter nodal rerun and smoke-test case
- final January member of the retained `v8` seasonal validation set

Case facts:
- source case: `ModelCases/GERMANY_PCM_nodal_case`
- study window: `2025-01-15 00:00:00` to `2025-01-17 00:00:00` (exclusive end)
- network, fleet, storage, and policy tables are copied from the full-year nodal master case
- hourly load, net imports, and generator availability are sliced to the selected 2-day window
- solved output is stored under `output/`

Validation notes:
- zero load shedding in the retained solved output
- total 2-day operating cost is about `$226.37M`
- uses the final winter `v8` resource-cost settings that are also propagated to the current dashboard bundle
