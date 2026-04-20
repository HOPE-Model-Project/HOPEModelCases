# Germany PCM HOPE Case Workspace

This folder is the preprocessing and documentation workspace for the current Germany PCM case suite in HOPE.

## Current recommended case set

Canonical full-year cases:
- `ModelCases/GERMANY_PCM_nodal_case`
- `ModelCases/GERMANY_PCM_zonal4_case`

Retained 2-day solved validation windows:
- `ModelCases/GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_apr15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_jul15_2day_resource_cost_case_v8`
- `ModelCases/GERMANY_PCM_nodal_oct15_2day_resource_cost_case_v8`

Legacy calibration-history cases are still present in `ModelCases/`, but they are not the primary examples anymore.

## Design rule

The Germany build uses one canonical nodal dataset first and derives the zonal case mechanically from it.

That means the intended geography is:

`Generator -> Bus -> Zone (TSO area) -> Germany`

and the intended comparison is:
- dispatch
- congestion
- curtailment
- interchange
- nodal price dispersion versus zonal price spreads

without calibrating nodal and zonal cases independently.

## Current active case characteristics

Nodal master case:
- 783 buses
- 1174 transmission edges
- 4267 generator rows
- 8760 hourly nodal-load rows
- 8760 hourly generator-availability rows

Zonal derivative case:
- 4 zones
- 5 interzonal interfaces
- 70 generator rows
- 8760 hourly regional-load rows

Current active modeling choices:
- four research zones based on the German TSOs:
  - `50Hertz`
  - `Amprion`
  - `TenneT`
  - `TransnetBW`
- no active nuclear rows in the 2025 fleet
- hourly net imports carried through the regional chronology
- hourly hydro, wind, and solar availability carried through `gen_availability_timeseries.csv`
- thermal operating assumptions differentiated by resource class, including lignite, hard coal, and multiple gas technologies

## Recommended build sequence

### Step 1. Nodal network backbone

Primary sources:
- OSM Europe transmission dataset from Xiong et al. 2025
- PyPSA-Eur base-network workflow

Goal:
- create a HOPE-friendly Germany nodal backbone with stable bus IDs, line connectivity, coordinates, and zone tags

### Step 2. Zone mapping

Build and freeze a bus-to-zone table for the four TSO regions.

This is the main consistency layer for both nodal and zonal cases.

### Step 3. Generator fleet

Primary source:
- `powerplantmatching`

Validation sources:
- BNetzA Marktstammdatenregister
- BNetzA Kraftwerksliste
- SMARD power plant map

Goal:
- assign each generator to one nodal bus once, then aggregate from that same mapping for the zonal case

### Step 4. Spatial nodal load allocation

Primary spatial-demand references:
- eGon-informed household and CTS demand structure where available
- public settlement and industry proxies for fallback spatial refinement

Goal:
- allocate TSO-area load to buses with stable spatial shares plus sectoral hourly variation

### Step 5. Chronology and availability

Primary chronology sources:
- SMARD
- OPSD where useful for convenience cross-checks

Goal:
- build full-year hourly load, net imports, and resource availability that are shared consistently across the nodal and zonal cases

### Step 6. Zonal derivative case

Goal:
- aggregate buses, generators, storage, and seams from the nodal master case
- derive zonal interface capacities from nodal cutsets instead of manual ATC guesses

## Workspace layout

- `raw_sources/`: manually downloaded upstream files and small calibration-side inputs
- `references/`: frozen mapping tables, source registers, and workflow notes
- `outputs/`: validation notes, templates, and intermediate exports
- `presentations/`: Germany case deck source files
- `build_germany_pcm_case.py`: nodal master-case build entry point
- `build_germany_zonal_case.py`: zonal derivative-case build entry point
- `build_germany_tso_geojson.py`: rebuild the dashboard-ready Germany TSO overlay
- `generate_germany_docs_map.py`: regenerate the Germany nodal map used in the docs
- `GERMANY_CASE_METHODS.md`: paper-style methods note for the active Germany build
- `GERMANY_CASE_HANDOFF.md`: practical guide to the recommended Germany example cases
- `SOURCE_MANIFEST.md`: source strategy and intended use

## Dashboard geometry

The Germany dashboard overlay uses a file-backed GeoJSON rather than bubble polygons.

Primary files:
- `tools/hope_dashboard/data/germany_tso_zones.geojson`
- `ModelCases/tools/germany_pcm_case_related/build_germany_tso_geojson.py`
- `ModelCases/tools/germany_pcm_case_related/raw_sources/reference_geo/germany_states_simplify200.geojson`

Interpretation:
- outer geometry comes from Germany state boundaries
- clearly covered states are assigned directly to one TSO region
- mixed states are split with the frozen Germany bus-zone layout as the seam guide

This is a research-grade reconstructed control-area overlay for dashboard use. It is more realistic than bubble polygons, but it is not an official TSO shapefile.
