# HOPEModelCases

Model case library for the [HOPE (Holistic Optimization Program for Electricity)](https://github.com/HOPE-Model-Project/HOPE) framework.

This repository contains input data, settings, and configuration files for running optimization scenarios with HOPE. Cases span a range of test systems (IEEE 14/118, RTS-24, ISONE, PJM, Germany) and study questions including expansion planning, production cost modeling, resource aggregation, and holistic planning runs.

## Getting started

### Option 1 — Clone into `HOPE/ModelCases/` (recommended)

Clone this repository directly into the `ModelCases/` folder inside your local HOPE directory. HOPE will find the cases automatically with no extra configuration.

```bash
# Step 1: Clone HOPE
git clone https://github.com/HOPE-Model-Project/HOPE

# Step 2: Clone HOPEModelCases into HOPE/ModelCases
git clone https://github.com/HOPE-Model-Project/HOPEModelCases HOPE/ModelCases
```

Then run any case from the Julia REPL (working directory: your `home` folder containing `HOPE/`):

```julia
using HOPE
HOPE.run_hope("HOPE/ModelCases/MD_GTEP_clean_case/")
```

To update your model cases later:

```bash
cd HOPE/ModelCases
git pull
```

### Option 2 — Clone anywhere and set an environment variable

Useful if you want to share one local copy of the model cases across multiple HOPE checkouts, or for CI environments.

```bash
git clone https://github.com/HOPE-Model-Project/HOPEModelCases ~/HOPEModelCases
```

Set `HOPE_MODELCASES_PATH` before running HOPE:

**Linux / macOS:**
```bash
export HOPE_MODELCASES_PATH=~/HOPEModelCases
```

**Windows (PowerShell):**
```powershell
$env:HOPE_MODELCASES_PATH = "C:\path\to\HOPEModelCases"
```

Then run any case using just the case name:

```julia
using HOPE
HOPE.run_hope("MD_GTEP_clean_case")
```

## Repository structure

Each case folder contains:

- `Data_<case_name>/` — input CSV files (generation, load, network, timeseries, etc.)
- `Settings/` — solver and model configuration YAML files
- `output/` — results written here after a run (not tracked by git)
- `README.md` — case-specific description (where available)

## Available cases

| Case | Mode | System |
|---|---|---|
| `MD_GTEP_clean_case` | GTEP | Maryland |
| `MD_GTEP_clean_fullchron_stressed_case` | GTEP | Maryland |
| `MD_PCM_Excel_case` | PCM | Maryland |
| `MD_PCM_Excel_DR_case` | PCM | Maryland (demand response) |
| `RTS24_PCM_case` | PCM | RTS-24 |
| `RTS24_PCM_fullfunc_case` | PCM | RTS-24 (full features) |
| `RTS24_PCM_multizone4_congested_1month_case` | PCM | RTS-24 multizone |
| `IEEE14_PCM_case` | PCM | IEEE 14-bus |
| `IEEE118_PCM_case` | PCM | IEEE 118-bus |
| `IEEE118_PCM_1month_case` | PCM | IEEE 118-bus (1 month) |
| `ISONE_PCM_250bus_case` | PCM | ISO-NE 250-bus |
| `PJM_MD100_GTEP_case` | GTEP | PJM / Maryland 100-bus |
| `PJM_MD100_PCM_case` | PCM | PJM / Maryland 100-bus |
| `GERMANY_PCM_nodal_case` | PCM | Germany nodal |
| `GERMANY_PCM_zonal4_case` | PCM | Germany 4-zone |
| `USA_64zone_GTEP_case` | GTEP | USA 64-zone |
| *(and more...)*  | | |

## License and citation

See the [HOPE repository](https://github.com/HOPE-Model-Project/HOPE) for license and citation information.
