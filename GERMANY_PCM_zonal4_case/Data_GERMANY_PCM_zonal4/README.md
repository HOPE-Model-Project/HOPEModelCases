# Data_GERMANY_PCM_zonal4

Direct-input data folder for the Germany 4-zone zonal derivative PCM case.

This case is derived mechanically from `GERMANY_PCM_nodal_case`.

Main contents:
- `zonedata.csv`: four Germany research zones aligned to the TSO regions
- `linedata.csv`: 5 aggregated interzonal interfaces built from nodal cross-zone cutsets
- `gendata.csv`: 70 aggregated generator rows by zone and resource class
- `storagedata.csv`: zonal storage aggregation from the nodal case
- `load_timeseries_regional.csv`: hourly regional load and `NI` chronology inherited from the nodal master case
- `wind_timeseries_regional.csv`, `solar_timeseries_regional.csv`: zonal VRE profiles inherited from the nodal master case
- `gen_availability_timeseries.csv`: hourly zonal availability file for aggregated hydro and VRE resources
- `carbonpolicies.csv`, `rpspolicies.csv`, `single_parameter.csv`: policy and scalar model inputs

Important interpretation notes:
- transmission seams are cutset-style reductions of the nodal seam set, not manually chosen ATC assumptions
- generator and storage fleets are aggregated from the nodal master case rather than independently calibrated
- this zonal case is intended as the consistency benchmark against the current nodal Germany baseline

See also:
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`
- `ModelCases/tools/germany_pcm_case_related/references/NETWORK_BACKBONE_WORKFLOW.md`
