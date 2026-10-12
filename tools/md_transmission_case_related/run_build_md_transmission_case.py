"""Fast entry point for build_md_transmission_case.py.

The wrapper adds bounding-box prefilters for detailed utility polygons, then calls
the reproducible case builder. It is kept separate so the core builder remains
easy to audit against the source-data transformations.
"""

from __future__ import annotations

from typing import Any

import build_md_transmission_case as builder


def bounded_utility_lookup(geojson: dict[str, Any]):
    features = []
    for feature in geojson.get("features", []):
        name = builder.utility_name(feature.get("properties") or {})
        if name not in builder.UTILITY_TO_ZONE:
            continue
        geometry = feature.get("geometry") or {}
        groups = geometry.get("coordinates", [])
        polygons = [groups] if geometry.get("type") == "Polygon" else groups
        points = [point for polygon in polygons for ring in polygon for point in ring]
        if not points:
            continue
        bounds = (
            min(point[0] for point in points),
            min(point[1] for point in points),
            max(point[0] for point in points),
            max(point[1] for point in points),
        )
        features.append((name, builder.UTILITY_TO_ZONE[name], geometry, bounds))

    def lookup(lon: float, lat: float) -> tuple[str, str] | None:
        for name, zone, geometry, (west, south, east, north) in features:
            if west <= lon <= east and south <= lat <= north:
                if builder.point_in_geometry(lon, lat, geometry):
                    return name, zone
        return None

    return lookup


if __name__ == "__main__":
    builder.build_utility_lookup = bounded_utility_lookup
    builder.main()
