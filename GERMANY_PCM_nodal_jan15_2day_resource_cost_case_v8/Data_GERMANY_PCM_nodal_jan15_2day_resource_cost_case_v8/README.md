# Data_GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8

Direct-input data folder for the January 15-17 2025 Germany nodal `v8` validation case.

This folder is a time-window derivative of `ModelCases/GERMANY_PCM_nodal_case`.

It keeps the same:
- bus, line, generator, storage, and policy tables
- four-zone Germany bus-to-zone geography
- resource-class operating assumptions

It changes only the time horizon:
- `load_timeseries_regional.csv`
- `load_timeseries_nodal.csv`
- `wind_timeseries_regional.csv`
- `solar_timeseries_regional.csv`
- `gen_availability_timeseries.csv`

The direct-input folder is paired with solved output under:
- `ModelCases/GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8/output`
