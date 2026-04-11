# Settlement And Industry OSM Notes

This note helps build the optional public spatial proxy layers:
- `settlement_centers.csv`
- `industrial_sites.csv`

The current HOPE builder only needs simple point CSVs with:
- `Longitude`
- `Latitude`
- `weight`

## Suggested sources

### Settlement layer

Use OSM place nodes or settlement centers as a lightweight urban-service proxy.

Examples of useful OSM tags:
- `place=city`
- `place=town`
- `place=village`
- optionally `place=suburb`

Simple weighting suggestion:
- city = 5
- town = 3
- village = 1
- suburb = 1

## Industry layer

Use OSM industrial points or centroids of industrial land-use polygons.

Examples of useful OSM tags:
- `landuse=industrial`
- `industrial=*`
- `man_made=works`

Simple weighting suggestion:
- each point = 1 by default
- if a size / area / employment proxy is available, use that instead

## Practical route

1. Query the data in Overpass Turbo or another OSM workflow.
2. Export points.
3. Convert to CSV with columns:
   - `Longitude`
   - `Latitude`
   - `weight`
4. Save as:
   - `settlement_centers.csv`
   - `industrial_sites.csv`

## HOPE weighting defaults

If all three layers exist, HOPE combines:
- population = 70%
- settlement = 15%
- industry = 15%

If only population exists, HOPE uses population alone.


## Quick conversion to HOPE CSV

Once you export a CSV from Overpass Turbo or another OSM workflow, convert it with:

```powershell
python tools/germany_pcm_case_related/raw_sources/public_spatial_load/convert_osm_points_to_hope.py your_settlement_export.csv --kind settlement
python tools/germany_pcm_case_related/raw_sources/public_spatial_load/convert_osm_points_to_hope.py your_industry_export.csv --kind industry
```
