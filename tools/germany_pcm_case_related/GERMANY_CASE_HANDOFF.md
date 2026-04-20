# Germany Case Handoff

## Purpose

This note is the practical handoff guide for the current Germany HOPE PCM example cases.

Use this file if you want to know:
- which Germany cases are the recommended examples now
- what assumptions they use
- what has already been validated
- what the key caveats still are

For the construction details, see:
- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`

## Recommended example set

Core cases to share:
- `ModelCases/GERMANY_PCM_nodal_case`
- `ModelCases/GERMANY_PCM_zonal4_case`
- `ModelCases/GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_apr15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_jul15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_oct15_2day_resource_cost_case_v8`

How to use them:
- `GERMANY_PCM_nodal_case` is the canonical full-year nodal source-of-truth case.
- `GERMANY_PCM_zonal4_case` is the mechanically derived zonal comparison case.
- `GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8` is the bundled dashboard demo and fastest winter rerun.
- the April, July, and October `v8` cases are the retained short seasonal cross-check windows.

Legacy cases to keep only for provenance:
- `GERMANY_PCM_nodal_jan_2day_rescaled_case`
- `GERMANY_PCM_nodal_jan_week1_connected_case`
- `GERMANY_PCM_nodal_jan_week3_baseline_case`
- `GERMANY_PCM_nodal_apr_week3_baseline_case`
- `GERMANY_PCM_nodal_jul_week3_baseline_case`
- `GERMANY_PCM_nodal_oct_week3_baseline_case`

## Current baseline assumptions

The active Germany baseline includes:
- transmission backbone built from cleaned Germany network staging tables
- frozen bus-to-zone mapping for the four TSO regions
- generator fleet mapped to buses from the cleaned `powerplantmatching`-based fleet
- offshore generator remapping that avoids weak radial coastal buses
- sector-differentiated nodal load construction with calibrated BTM-PV
- hourly net imports carried through the regional chronology
- hourly hydro, wind, and solar availability in `gen_availability_timeseries.csv`
- thermal operating assumptions differentiated by resource class, including lignite, hard coal, and multiple gas technologies

Important modeling choice:
- the zonal case is derived mechanically from the nodal master assumptions
- zonal and nodal cases are not calibrated independently

## Nodal versus zonal interpretation

Held aligned as much as possible:
- study year and chronology
- zonal load totals
- zonal renewable profile shapes
- technology-cost assumptions
- technology-operating assumptions
- total capacity by zone and technology
- storage capacity by zone and storage type
- policy settings

Changed between the two cases:
- nodal case represents within-zone network detail; zonal case does not
- nodal case can have internal congestion inside a TSO; zonal case cannot
- nodal case places assets and load at bus level; zonal case aggregates them to zone level
- nodal and zonal cases do not have the same number of generator rows

The fairness criterion is consistency of the underlying fleet and assumptions, not equality of row counts.

## Fleet and cost resolution

The current Germany fleet is not using plant-specific operating costs.

What is plant/resource-resolved:
- generator rows are mapped to specific buses from the cleaned Germany fleet
- zonal aggregation is built from that mapped nodal fleet

What is still technology-class based:
- variable cost
- emissions factor
- capacity credit
- outage assumptions
- ramp assumptions
- reserve assumptions
- startup and minimum up/down assumptions

So the fleet has plant/bus placement detail, but the operating-cost layer is still resource-class based rather than plant-specific.

The active 2025 build contains no nuclear rows.

## What has been validated already

The current Germany baseline has passed these checks:

### 1. Offshore artifact removal

- earlier artificial coastal `TenneT` bottlenecks caused by bad offshore mapping were removed
- the model still shows northern stress after the fix, which is the intended directional outcome

### 2. Short-window seasonal validation

The retained final `v8` 2-day pack is:
- `GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_apr15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_jul15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_oct15_2day_resource_cost_case_v8`

Main result:
- all four retained 2-day cases solve with zero load shedding
- the January `v8` case is the dashboard default
- dispatch behavior is materially improved relative to the older January rescaled case

### 3. BTM-PV promotion

The calibrated `base` BTM-PV treatment is still the preferred operating baseline because it improves summer net-load behavior without destabilizing winter behavior.

## Main caveats

The current Germany cases are strong research examples, but they are not a fully plant-cost-calibrated historical benchmark.

Main caveats:
- industry demand is still partly proxy-based because direct industry demand data is incomplete
- empirical validation is still directional rather than corridor-by-corridor
- wind and solar availability still use nationally shaped hourly chronology rather than weather-resolved zonal or nodal fields
- hydro availability is hourly, but it is still national-history based rather than basin-resolved
- broader prosumer effects such as EV charging and heat pumps are not included

## Quick explanation of the nodal load model

If you need a short explanation for a colleague:

1. start from hourly TSO-area load
2. allocate zonal load to buses using stable spatial shares informed by eGon households and CTS plus an industry proxy
3. reshape hourly bus load with sector-specific activity so buses in the same TSO do not all have identical profiles
4. subtract calibrated BTM-PV from the non-industry component to approximate transmission-visible net load

## What to run first

Recommended sequence for a new user:

1. compare `GERMANY_PCM_zonal4_case` against `GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
2. use `GERMANY_PCM_nodal_case` when you need the canonical full-year nodal source data
3. use the April, July, and October `v8` windows as quick seasonal cross-checks

## Best companion files to share

- `ModelCases/tools/germany_pcm_case_related/GERMANY_CASE_METHODS.md`
- `ModelCases/tools/germany_pcm_case_related/outputs/germany_current_baseline_validation_memo.md`
- `docs/src/case_germany_pcm.md`

## Bottom line

If someone asks, "Which Germany examples should I use?", the short answer is:

- `GERMANY_PCM_nodal_case`
- `GERMANY_PCM_zonal4_case`
- `GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
- the other retained seasonal `v8` 2-day cases when you want spring, summer, and autumn cross-checks
