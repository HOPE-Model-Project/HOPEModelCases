# Data_GERMANY_PCM_nodal

Direct-input data folder for the canonical Germany nodal HOPE PCM case.

Main contents:
- `zonedata.csv`: four Germany research zones aligned to the TSO regions
- `busdata.csv`: 783 retained buses after connected-component filtering and frozen bus-zone mapping
- `linedata.csv`: 1174 HOPE transmission edges assembled from cleaned lines and transformers
- `gendata.csv`: 4267 generator rows from the cleaned Germany fleet with bus assignments and resource-class operating assumptions
- `storagedata.csv`: mapped storage subset aggregated to HOPE storage records
- `load_timeseries_regional.csv`: hourly regional load chronology with `NI` net-import column
- `load_timeseries_nodal.csv`: hourly nodal net load after sectoral spatial allocation and BTM-PV adjustment
- `wind_timeseries_regional.csv` and `solar_timeseries_regional.csv`: hourly regional VRE profiles
- `gen_availability_timeseries.csv`: hourly generator-level availability for hydro and VRE resources
- `carbonpolicies.csv`, `rpspolicies.csv`, `single_parameter.csv`: policy and scalar model inputs

Primary source stack:
- cleaned Germany network staging tables derived from the OSM Europe transmission dataset with PyPSA-Eur workflow reference
- cleaned Germany fleet derived from `powerplantmatching` with BNetzA and SMARD validation support
- SMARD national load/generation chronology plus four TSO-area load helper files
- frozen spatial load-share workflow using eGon-informed household and CTS structure plus an industry proxy

Important process notes:
- the active fleet contains no nuclear rows in the current 2025 case
- zonal load is allocated to buses with sector-differentiated hourly weights and then adjusted with calibrated BTM-PV
- hourly wind, solar, and hydro availability is file-backed through `gen_availability_timeseries.csv`
- this folder is the build source for `GERMANY_PCM_zonal4_case` and for the retained 2-day validation derivatives

See also:
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`
- `ModelCases/tools/germany_pcm_case_related/references/CHRONOLOGY_WORKFLOW.md`
- `ModelCases/tools/germany_pcm_case_related/references/GENERATOR_FLEET_WORKFLOW.md`
