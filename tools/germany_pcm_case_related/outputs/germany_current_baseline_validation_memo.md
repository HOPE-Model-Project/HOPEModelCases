# Germany Current Baseline Validation Memo

## Purpose

This memo freezes the currently preferred Germany PCM baseline after the latest dispatch-improvement pass, seasonal `v8` short-window checks, and dashboard update.

## Current promoted baseline

The current Germany baseline now includes:
- spatial nodal load allocation built from eGon-informed households and CTS structure plus the current industry proxy
- sector-differentiated nodal hourly load construction
- calibrated base BTM-PV net-load correction
- offshore generator remapping that avoids weak radial coastal buses
- hourly hydro, wind, and solar availability through `gen_availability_timeseries.csv`
- no active nuclear rows in the 2025 fleet

The active benchmark cases are now:
- `GERMANY_PCM_nodal_case`
- `GERMANY_PCM_zonal4_case`
- `GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_apr15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_jul15_2day_resource_cost_case_v8`
- `GERMANY_PCM_nodal_oct15_2day_resource_cost_case_v8`

## Validation status

Current readout:
- all four retained `v8` 2-day windows solve with zero load shedding
- the January `v8` case is the dashboard default
- dispatch behavior is materially improved relative to the older January rescaled case
- the broad congestion geography remains directionally credible

The directional empirical benchmark still looks like:
- northern or northwestern export-side stress
- west-central `Amprion` corridor stress
- southwest `TransnetBW` receiving-area stress

## BTM-PV decision

The calibrated base BTM-PV layer remains the preferred Germany operating baseline.

Why:
- winter response stays modest
- summer response is meaningful but smooth
- congestion geography changes more in intensity than in location

## Remaining caveats

Main caveats:
- industry demand is still partly proxy-based
- validation is still directional rather than corridor-by-corridor
- wind and solar availability are still nationally shaped rather than weather-resolved by zone or bus
- hydro availability is hourly but still national-history based rather than basin-resolved
- broader prosumer effects like EV charging and heat pumps are not yet modeled

## Recommended use

Use this baseline for:
- exploratory Germany nodal research
- dashboard and documentation examples
- zonal-versus-nodal comparison under consistent assumptions
- future empirical validation and cost-refinement work
