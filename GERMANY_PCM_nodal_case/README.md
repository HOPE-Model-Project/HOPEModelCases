# GERMANY_PCM_nodal_case

Canonical full-year Germany nodal PCM master case for HOPE.

Current role:
- source-of-truth Germany nodal case for the 2025 Germany PCM build
- basis for the 4-zone zonal derivative case and the retained 2-day seasonal validation windows
- reference case for Germany dashboard, methods, and preprocessing documentation

Current contents:
- 783 buses
- 1174 transmission edges in `linedata.csv`
- 4267 generator rows in `gendata.csv`
- 8760 hourly rows in `load_timeseries_nodal.csv`
- 8760 hourly rows in `gen_availability_timeseries.csv`
- four research zones: `50Hertz`, `Amprion`, `TenneT`, `TransnetBW`

Key modeling notes:
- the active 2025 fleet excludes nuclear generation in the current build
- hourly net imports are carried through the regional chronology via the `NI` column in `load_timeseries_regional.csv`
- `gen_availability_timeseries.csv` provides hourly hydro, wind, and solar availability at generator resolution
- thermal operating assumptions are differentiated by resource class, including lignite, hard coal, and multiple gas technologies

Direct input folder:
- `Data_GERMANY_PCM_nodal/`

Companion documentation:
- `ModelCases/tools/germany_pcm_case_related/README.md`
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_HANDOFF.md`
