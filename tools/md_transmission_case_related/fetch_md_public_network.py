from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
RAW_DIR = TOOLS_DIR / "raw_sources"
TILE_DIR = RAW_DIR / "osm_tiles"
REF_DIR = TOOLS_DIR / "references"
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
UTILITY_URL = (
    "https://services.arcgis.com/njFNhDsUCentVYJW/ArcGIS/rest/services/"
    "UtilityPolygons/FeatureServer/0/query"
)
MARYLAND_BUFFER_BBOX = (37.55, -79.90, 40.15, -74.65)
TRANSMISSION_VOLTAGES = (
    "69000",
    "115000",
    "138000",
    "230000",
    "345000",
    "500000",
    "765000",
)


def build_query(bbox: tuple[float, float, float, float]) -> str:
    bbox_text = ",".join(str(value) for value in bbox)
    voltage_regex = "(^|;)(" + "|".join(TRANSMISSION_VOLTAGES) + ")(;|$)"
    return f"""
[out:json][timeout:300][maxsize:536870912];
(
  nwr["power"="substation"]["voltage"~"{voltage_regex}"]({bbox_text});
  way["power"="line"]["voltage"~"{voltage_regex}"]({bbox_text});
  way["power"="cable"]["voltage"~"{voltage_regex}"]({bbox_text});
);
out body center geom tags;
""".strip()


def tiles(
    bbox: tuple[float, float, float, float], tile_degrees: float
) -> list[tuple[float, float, float, float]]:
    south, west, north, east = bbox
    result: list[tuple[float, float, float, float]] = []
    lat = south
    while lat < north:
        lon = west
        tile_north = min(north, lat + tile_degrees)
        while lon < east:
            tile_east = min(east, lon + tile_degrees)
            result.append((lat, lon, tile_north, tile_east))
            lon = tile_east
        lat = tile_north
    return result


def get_json(url: str, *, data: bytes | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "HOPE-Maryland-Transmission-Case/0.1"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_tile(query: str, attempts: int = 6) -> tuple[dict[str, Any], str]:
    encoded = urllib.parse.urlencode({"data": query}).encode("utf-8")
    failures: list[str] = []
    for attempt in range(attempts):
        endpoint = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            return get_json(endpoint, data=encoded), endpoint
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{endpoint}: {type(exc).__name__}: {exc}")
            if attempt + 1 < attempts:
                delay = min(45, 8 * (attempt + 1))
                print(f"  retrying after {delay}s: {failures[-1]}", flush=True)
                time.sleep(delay)
    raise RuntimeError("Overpass tile failed after retries:\n" + "\n".join(failures))


def tile_path(index: int, bbox: tuple[float, float, float, float]) -> Path:
    digest = hashlib.sha256(repr(bbox).encode("utf-8")).hexdigest()[:10]
    return TILE_DIR / f"tile_{index:02d}_{digest}.json"


def summarize(elements: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    with_circuits = 0
    for element in elements:
        tags = element.get("tags") or {}
        power = str(tags.get("power", "unknown"))
        counts[power] = counts.get(power, 0) + 1
        with_circuits += int(bool(tags.get("circuits")))
    return {
        "element_count": len(elements),
        "by_power_type": counts,
        "with_circuits_tag": with_circuits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resumable public-data fetch for the Maryland HOPE transmission case."
    )
    parser.add_argument("--tile-degrees", type=float, default=1.0)
    parser.add_argument("--pause-seconds", type=float, default=10.0)
    args = parser.parse_args()

    TILE_DIR.mkdir(parents=True, exist_ok=True)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    all_elements: dict[tuple[str, int], dict[str, Any]] = {}
    tile_log: list[dict[str, Any]] = []
    all_tiles = tiles(MARYLAND_BUFFER_BBOX, args.tile_degrees)

    for index, bbox in enumerate(all_tiles, start=1):
        cached = tile_path(index, bbox)
        if cached.exists():
            payload = json.loads(cached.read_text(encoding="utf-8"))
            endpoint = "cache"
        else:
            payload, endpoint = fetch_tile(build_query(bbox))
            cached.write_text(json.dumps(payload), encoding="utf-8")
            if index < len(all_tiles):
                time.sleep(max(0.0, args.pause_seconds))
        returned = payload.get("elements", [])
        for element in returned:
            all_elements[(str(element.get("type")), int(element.get("id")))] = element
        tile_log.append(
            {
                "tile": index,
                "bbox": bbox,
                "endpoint": endpoint,
                "returned_elements": len(returned),
            }
        )
        print(f"Loaded tile {index}/{len(all_tiles)}: {len(returned)} elements ({endpoint})", flush=True)

    osm = {"version": 0.6, "elements": list(all_elements.values())}
    osm_path = RAW_DIR / "osm_power_maryland_buffer.json"
    osm_path.write_text(json.dumps(osm), encoding="utf-8")

    utility_path = RAW_DIR / "maryland_utility_polygons.geojson"
    if utility_path.exists():
        utility = json.loads(utility_path.read_text(encoding="utf-8"))
    else:
        params = urllib.parse.urlencode(
            {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
            }
        )
        utility = get_json(f"{UTILITY_URL}?{params}")
        utility_path.write_text(json.dumps(utility), encoding="utf-8")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "osm_source": "OpenStreetMap contributors via Overpass API",
        "osm_license": "ODbL 1.0",
        "bbox": MARYLAND_BUFFER_BBOX,
        "transmission_voltages_v": list(TRANSMISSION_VOLTAGES),
        "tiles": tile_log,
        "osm_summary": summarize(osm["elements"]),
        "utility_source": UTILITY_URL,
        "utility_feature_count": len(utility.get("features", [])),
    }
    path = REF_DIR / "source_fetch_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
