# RTS24 DART case

This is a standalone, all-compatible-constraints DART case for the modified
HOPE RTS24 system. It uses the same case workflow as PCM and GTEP:

- `Settings/HOPE_model_settings.yml` selects `model_mode: DART` and configures
  the run;
- `Data_RTS24_DART/` contains physical, chronological, state, and DART-specific
  input data;
- the standard `run_hope` API validates, solves, and writes `output/`.

The case has 24 buses, 38 circuits, 33 generators, five batteries, and 8,760
hourly source observations. `stable_ids.csv` provides durable asset identities,
and `manifest.yml` pins every input with SHA-256.

## Run

From the HOPE repository root:

```julia
using HOPE
validate_hope("ModelCases/RTS24_DART_case")
results = run_hope("ModelCases/RTS24_DART_case")
```

The compatibility wrapper provides the same operations:

```text
julia --project=. ModelCases/RTS24_DART_case/run_case.jl validate
julia --project=. ModelCases/RTS24_DART_case/run_case.jl run
```

## DART-specific inputs

The normal HOPE physical files remain canonical. DART-specific static asset
attributes are merged into those files instead of being split across
supplemental tables:

- `gendata.csv` contains quick-start status and response time, transition
  limits, no-load/shutdown costs, NSPIN capability, and reserve offers;
- `storagedata.csv` contains storage reserve capabilities and reserve offers;
- `initial_generator_state.csv` contains commitment, output, service status,
  and prior online/offline durations;
- `initial_storage_state.csv` contains initial state of charge.

Native real-time trajectories are explicit 24-hour, five-minute inputs:
`load_timeseries_realtime_regional.csv`,
`wind_timeseries_realtime_regional.csv`, and
`solar_timeseries_realtime_regional.csv`. Each has 288 rows and a `Minute`
column containing 0, 5, ..., 55 for every hour. The hourly regional files still
supply the day-ahead forecast.

If no native RT files are configured, HOPE warns that it is repeating or
legacy-shaping hourly data. If RT files are configured without `Minute`, HOPE
warns and rejects them because their chronology cannot be verified.

The settings file defines the DA/RT horizons, physical outage, generator
contingency, balanced interchange, five-minute realization, settlement, and
acceptance thresholds.

## Constraint coverage

The reference run requires all 19 compatible DART constraint families:

- binary DA commitment, startup/shutdown, minimum up/down times, and initial
  duration obligations;
- DA/RT ramps, transition limits, and four reserve products including offline
  quick-start NSPIN;
- storage chronology, efficiency, operating mode, reserves, and terminal SOC;
- nodal balance, PTDF flows, line limits, and balanced interchange;
- strict generator N-1 security and a realized RT generator outage;
- DA forecasts, five-minute RT deviations, fixed-commitment RT SCED, rolling
  state handoff, pricing, and two-settlement accounting.

`output/constraint_coverage.csv` and `output/acceptance_summary.csv` provide
machine-readable verification. Generic FOR derating is disabled because this
case uses an explicit physical outage. DART currently supports generator, not
line, contingencies and does not implement planning, representative-day,
policy, aggregation, or flexible-demand features. If one of those common HOPE
features is enabled, validation emits a warning and stops before model
construction instead of silently ignoring it.
