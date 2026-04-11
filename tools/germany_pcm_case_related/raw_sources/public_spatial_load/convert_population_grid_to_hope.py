from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import pandas as pd
from pyproj import Transformer


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / 'population_grid_1km.csv'


def _find_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    lowered = {str(col).strip().lower(): col for col in frame.columns}
    for candidate in candidates:
        found = lowered.get(candidate.lower())
        if found is not None:
            return found
    return None


def _load_any_csv(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as zf:
            csv_names = [name for name in zf.namelist() if name.lower().endswith('.csv')]
            if not csv_names:
                raise FileNotFoundError(f'No CSV found inside {path}')
            # Prefer files that look like 1km population extracts.
            csv_names.sort(key=lambda n: ('1km' not in n.lower(), 'pop' not in n.lower(), len(n)))
            with zf.open(csv_names[0]) as fh:
                return pd.read_csv(fh, sep=None, engine='python')
    return pd.read_csv(path, sep=None, engine='python')


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert a Germany population-grid CSV/ZIP into HOPE population_grid_1km.csv format.')
    parser.add_argument('input_path', help='Path to a downloaded CSV or ZIP containing gridded population data')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Output CSV path')
    args = parser.parse_args()

    input_path = Path(args.input_path)
    out_path = Path(args.output)
    frame = _load_any_csv(input_path)

    lon_col = _find_column(frame, ('longitude', 'lon', 'x', 'rechtswert', 'x_mp_1km', 'x_mp_100m', 'x_mp_10km'))
    lat_col = _find_column(frame, ('latitude', 'lat', 'y', 'hochwert', 'y_mp_1km', 'y_mp_100m', 'y_mp_10km'))
    pop_col = _find_column(frame, ('population', 'pop', 'einwohner', 'value', 'obs_value', 'count', 'anzahl'))

    if lon_col is None or lat_col is None or pop_col is None:
        raise KeyError(
            'Could not identify longitude/latitude/population columns. '            f'Found columns: {list(frame.columns)}'
        )

    out = frame[[lon_col, lat_col, pop_col]].copy()
    out.columns = ['Longitude', 'Latitude', 'Population']
    out['Longitude'] = pd.to_numeric(out['Longitude'], errors='coerce')
    out['Latitude'] = pd.to_numeric(out['Latitude'], errors='coerce')
    out['Population'] = pd.to_numeric(out['Population'], errors='coerce')

    # Official Zensus grid exports use EPSG:3035 meter coordinates in x_mp/y_mp fields.
    if out['Longitude'].abs().median() > 1000 or out['Latitude'].abs().median() > 1000:
        transformer = Transformer.from_crs('EPSG:3035', 'EPSG:4326', always_xy=True)
        lon, lat = transformer.transform(out['Longitude'].to_numpy(dtype=float), out['Latitude'].to_numpy(dtype=float))
        out['Longitude'] = lon
        out['Latitude'] = lat
    out = out.dropna(subset=['Longitude', 'Latitude', 'Population'])
    out = out.loc[out['Population'] > 0].copy()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f'Wrote {out_path} with {len(out)} rows')


if __name__ == '__main__':
    main()
