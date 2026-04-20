# GERMANY_PCM_zonal4_case

Active full-year Germany 4-zone zonal derivative case aligned to the current Germany nodal master case.

Current role:
- consistency benchmark for nodal-versus-zonal Germany PCM comparison
- mechanically aggregated derivative of `GERMANY_PCM_nodal_case`
- companion case for dashboard and documentation examples

Current contents:
- 4 zones: `50Hertz`, `Amprion`, `TenneT`, `TransnetBW`
- 5 interzonal interfaces in `linedata.csv`
- 70 generator rows in `gendata.csv`
- 8760 hourly rows in `load_timeseries_regional.csv`
- 8760 hourly rows in `gen_availability_timeseries.csv`

Key modeling notes:
- zonal transmission seams are aggregated from nodal cross-zone cutsets
- zonal load chronology is inherited from the nodal master case, including the promoted BTM-PV net-load treatment and hourly net imports
- zonal generator and storage fleets are aggregated from the nodal fleet rather than rebuilt independently
- the zonal fleet also contains no nuclear rows in the active 2025 build

Direct input folder:
- `Data_GERMANY_PCM_zonal4/`

Companion documentation:
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_HANDOFF.md`
