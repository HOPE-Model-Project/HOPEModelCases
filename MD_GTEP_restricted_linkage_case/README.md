# Maryland restricted GTEP-to-PCM linkage benchmark

This compact 24-hour GTEP case is paired with `../MD_PCM_restricted_linkage_case`. It uses two
real Maryland OSM transmission identifiers but deliberately reduced study
ratings and synthetic operating assumptions to make linkage behavior observable.

The case is an integration/acceptance benchmark, not a forecast of the Maryland
system. It is designed to produce nonzero retirement, generation, storage, and
transmission decisions while exercising binary investment, zonal planning
reserve, spinning reserve, RPS, demand response, and transmission losses.

Carbon-policy alternatives, resource aggregation, endogenous representative-day
selection, and interregional net interchange are intentionally left to focused
tests. The GTEP case does use an external representative-period weight so the
24-hour operations are annualized.

Run the complete pair with:

```julia
include("run_holistic_pair.jl")
```

The paired PCM output writes `holistic_coverage.yml` and
`holistic_coverage.csv`; the run fails if a required acceptance check fails.
