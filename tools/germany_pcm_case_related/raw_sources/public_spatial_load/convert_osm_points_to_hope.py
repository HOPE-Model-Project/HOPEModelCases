from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_SETTLEMENT = HERE / 'settlement_centers.csv'
DEFAULT_INDUSTRY = HERE / 'industrial_sites.csv'
SETTLEMENT_WEIGHTS = {
    'city': 5.0,
    'town': 3.0,
    'village': 1.0,
    'suburb': 1.0,
    'hamlet': 0.5,
}


def _find_column(frame: pd.DataFrame, candidates: tuple[str, ...], required: bool = True) -> str | None:
    lowered = {str(col).strip().lower(): col for col in frame.columns}
    for candidate in candidates:
        found = lowered.get(candidate.lower())
        if found is not None:
            return found
    if required:
        raise KeyError(f'Expected one of {candidates}; found {list(frame.columns)}')
    return None


def _flatten_coords(coords):
    if isinstance(coords, (list, tuple)) and coords and isinstance(coords[0], (int, float)):
        return [coords]
    points = []
    if isinstance(coords, (list, tuple)):
        for item in coords:
            points.extend(_flatten_coords(item))
    return points


def _load_geojson(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding='utf-8'))
    features = payload.get('features', [])
    rows = []
    for feature in features:
        props = feature.get('properties', {}) or {}
        geom = feature.get('geometry', {}) or {}
        lon = props.get('@lon') or props.get('lon') or props.get('longitude')
        lat = props.get('@lat') or props.get('lat') or props.get('latitude')
        if lon is None or lat is None:
            coords = _flatten_coords(geom.get('coordinates'))
            if coords:
                xs = [float(pt[0]) for pt in coords if len(pt) >= 2]
                ys = [float(pt[1]) for pt in coords if len(pt) >= 2]
                if xs and ys:
                    lon = sum(xs) / len(xs)
                    lat = sum(ys) / len(ys)
        rows.append({
            'longitude': lon,
            'latitude': lat,
            'place': props.get('place') or props.get('type'),
            'weight': props.get('weight') or props.get('value') or props.get('population'),
            'name': props.get('name'),
            'industrial': props.get('industrial'),
            'landuse': props.get('landuse'),
        })
    return pd.DataFrame(rows)


def _load_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {'.geojson', '.json'}:
        return _load_geojson(path)
    return pd.read_csv(path, sep=None, engine='python')


def _has_positive_weights(frame: pd.DataFrame, column: str) -> bool:
    values = pd.to_numeric(frame[column], errors='coerce')
    return bool(values.notna().any() and (values.fillna(0.0) > 0).any())


def main() -> None:
    parser = argparse.ArgumentParser(description='Convert an OSM/Overpass CSV or GeoJSON to a HOPE settlement or industry point layer.')
    parser.add_argument('input_path', help='Input CSV or GeoJSON exported from OSM / Overpass / GIS workflow')
    parser.add_argument('--kind', choices=['settlement', 'industry'], required=True)
    parser.add_argument('--output', help='Output CSV path')
    args = parser.parse_args()

    input_path = Path(args.input_path)
    frame = _load_input(input_path)

    lon_col = _find_column(frame, ('longitude', 'lon', 'x', '@lon'))
    lat_col = _find_column(frame, ('latitude', 'lat', 'y', '@lat'))
    weight_col = _find_column(frame, ('weight', 'Weight', 'value', 'Value', 'population', 'Population'), required=False)
    place_col = _find_column(frame, ('place', 'Place', 'settlement_type', 'type'), required=False)

    out = frame[[lon_col, lat_col] + ([weight_col] if weight_col else []) + ([place_col] if place_col else [])].copy()
    out.columns = ['Longitude', 'Latitude'] + (['raw_weight'] if weight_col else []) + (['place'] if place_col else [])
    out['Longitude'] = pd.to_numeric(out['Longitude'], errors='coerce')
    out['Latitude'] = pd.to_numeric(out['Latitude'], errors='coerce')
    out = out.dropna(subset=['Longitude', 'Latitude']).copy()

    if args.kind == 'settlement':
        if 'raw_weight' in out.columns and _has_positive_weights(out, 'raw_weight'):
            out['SettlementWeight'] = pd.to_numeric(out['raw_weight'], errors='coerce').fillna(0.0)
        elif 'place' in out.columns:
            out['SettlementWeight'] = out['place'].astype(str).str.lower().map(SETTLEMENT_WEIGHTS).fillna(1.0)
        else:
            out['SettlementWeight'] = 1.0
        out = out.loc[out['SettlementWeight'] > 0].copy()
        final = out[['Longitude', 'Latitude', 'SettlementWeight']]
        out_path = Path(args.output) if args.output else DEFAULT_SETTLEMENT
    else:
        if 'raw_weight' in out.columns and _has_positive_weights(out, 'raw_weight'):
            out['IndustrialWeight'] = pd.to_numeric(out['raw_weight'], errors='coerce').fillna(0.0)
        else:
            out['IndustrialWeight'] = 1.0
        out = out.loc[out['IndustrialWeight'] > 0].copy()
        final = out[['Longitude', 'Latitude', 'IndustrialWeight']]
        out_path = Path(args.output) if args.output else DEFAULT_INDUSTRY

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(out_path, index=False)
    print(f'Wrote {out_path} with {len(final)} rows')


if __name__ == '__main__':
    main()
