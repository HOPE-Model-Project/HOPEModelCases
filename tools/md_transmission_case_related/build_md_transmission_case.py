from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


TOOLS_DIR = Path(__file__).resolve().parent
MODELCASES_DIR = TOOLS_DIR.parents[1]
WORKSPACE_DIR = MODELCASES_DIR.parent
RAW_DIR = TOOLS_DIR / "raw_sources"
CASE_DIR = MODELCASES_DIR / "MD_PCM_transmission_public_case"
DATA_DIR = CASE_DIR / "Data_MD_PCM_transmission_public"
REF_DIR = CASE_DIR / "references"

MD100_DIR = MODELCASES_DIR / "PJM_MD100_PCM_case" / "Data_PJM_PCM_subzones"
PJM_SOURCE_DIR = (
    WORKSPACE_DIR
    / "PJM_DC_health_study_project"
    / "ModelCases"
    / "PJM_ICARUS21_PCM_2025_Base_case"
    / "Data_PJM_ICARUS21_PCM_2025_Base"
)

ALLOWED_KV = (69, 115, 138, 230, 345, 500, 765)
ZONE_PEAKS = {
    "APS_MD": 2326.75,
    "BGE": 6520.0,
    "DPL_MD": 818.5,
    "PEPCO": 10097.9,
}
SOURCE_ZONE = {"APS_MD": "APS", "BGE": "BGE", "DPL_MD": "DPL", "PEPCO": "PEPCO"}
UTILITY_TO_ZONE = {
    "Allegheny Power": "APS_MD",
    "City of Hagerstown Light Department": "APS_MD",
    "Thurmont Municipal Light Company": "APS_MD",
    "Williamsport Municipal Light Company": "APS_MD",
    "Baltimore Gas and Electric Company": "BGE",
    "Berlin Municipal Electric Plant": "DPL_MD",
    "Choptank Electric Cooperative, Inc.": "DPL_MD",
    "Delmarva Power": "DPL_MD",
    "Easton Utilities Comission": "DPL_MD",
    "Somerset Rural Electric Cooperative": "DPL_MD",
    "Potomac Electric Power Company": "PEPCO",
    "Southern Maryland Electric Cooperative": "PEPCO",
}
RATING_MW = {69: 100.0, 115: 200.0, 138: 300.0, 230: 600.0, 345: 1200.0, 500: 2000.0, 765: 3500.0}


def parse_voltage(value: Any) -> list[int]:
    values: list[int] = []
    text = str(value or "")
    for token in text.replace(",", ";").split(";"):
        try:
            raw = float(token.strip())
        except ValueError:
            continue
        kv = int(round(raw / 1000.0 if raw > 1000 else raw))
        if kv in ALLOWED_KV:
            values.append(kv)
    return sorted(set(values))


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside = False
    if len(ring) < 3:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][:2]
        xj, yj = ring[j][:2]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1.0e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def point_in_geometry(lon: float, lat: float, geometry: dict[str, Any]) -> bool:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates", [])
    polygons = [coordinates] if kind == "Polygon" else coordinates if kind == "MultiPolygon" else []
    for polygon in polygons:
        if polygon and point_in_ring(lon, lat, polygon[0]):
            if not any(point_in_ring(lon, lat, hole) for hole in polygon[1:]):
                return True
    return False


def utility_name(properties: dict[str, Any]) -> str:
    for key in ("NAME", "Name", "UTILITY", "Utility", "UTIL_NAME", "Company"):
        if properties.get(key):
            return str(properties[key])
    for value in properties.values():
        if str(value) in UTILITY_TO_ZONE:
            return str(value)
    return ""


def build_utility_lookup(geojson: dict[str, Any]):
    features = []
    for feature in geojson.get("features", []):
        name = utility_name(feature.get("properties") or {})
        if name in UTILITY_TO_ZONE:
            features.append((name, UTILITY_TO_ZONE[name], feature.get("geometry") or {}))

    def lookup(lon: float, lat: float) -> tuple[str, str] | None:
        for name, zone, geometry in features:
            if point_in_geometry(lon, lat, geometry):
                return name, zone
        return None

    return lookup


def coords(element: dict[str, Any]) -> list[tuple[float, float]]:
    geometry = element.get("geometry") or []
    points = [
        (float(point["lon"]), float(point["lat"]))
        for point in geometry
        if point.get("lon") is not None and point.get("lat") is not None
    ]
    if points:
        return points
    center = element.get("center") or {}
    if center.get("lon") is not None and center.get("lat") is not None:
        return [(float(center["lon"]), float(center["lat"]))]
    if element.get("lon") is not None and element.get("lat") is not None:
        return [(float(element["lon"]), float(element["lat"]))]
    return []


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(h)))


def line_length_km(points: list[tuple[float, float]]) -> float:
    return sum(haversine_km(a, b) for a, b in zip(points, points[1:]))


def circuits(tags: dict[str, Any]) -> int:
    try:
        return max(1, int(float(str(tags.get("circuits", "")).split(";")[0])))
    except ValueError:
        try:
            return max(1, int(round(float(tags.get("cables", 3))) // 3))
        except (TypeError, ValueError):
            return 1


def nearest_bus(
    lon: float,
    lat: float,
    kv: int,
    candidates: list[dict[str, Any]],
    max_km: float,
) -> dict[str, Any] | None:
    compatible = [b for b in candidates if b["kv"] == kv]
    if not compatible:
        return None
    best = min(compatible, key=lambda b: haversine_km((lon, lat), (b["lon"], b["lat"])))
    return best if haversine_km((lon, lat), (best["lon"], best["lat"])) <= max_km else None


def choose_gen_bus(row: pd.Series, buses: list[dict[str, Any]]) -> dict[str, Any]:
    zone_map = {"APS": "APS_MD", "BGE": "BGE", "DPL": "DPL_MD", "PEPCO": "PEPCO"}
    target_zone = zone_map.get(str(row["Zone"]), str(row["Zone"]))
    pmax = float(row["Pmax (MW)"])
    minimum_kv = 230 if pmax >= 500 else 115 if pmax >= 100 else 69
    pool = [b for b in buses if b["zone"] == target_zone and b["kind"] == "substation" and b["kv"] >= minimum_kv]
    if not pool:
        pool = [b for b in buses if b["zone"] == target_zone and b["kind"] == "substation"]
    if not pool:
        pool = [b for b in buses if b["zone"] == target_zone]
    if not pool:
        pool = [b for b in buses if b["zone"] != "EXT"]
    return min(pool, key=lambda b: haversine_km((float(row["Longitude"]), float(row["Latitude"])), (b["lon"], b["lat"])))


def time_window(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[(frame["Month"] == 7) & (frame["Day"].between(15, 21))].copy()
    if len(result) != 168:
        raise RuntimeError(f"Expected 168 July 15-21 rows, found {len(result)}")
    result["Time Period"] = 1
    return result.reset_index(drop=True)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, lineterminator="\n")


def connected_components(buses: list[dict[str, Any]], branches: list[dict[str, Any]]) -> dict[str, int]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for branch in branches:
        a, b = branch["from_bus"], branch["to_bus"]
        adjacency[a].add(b)
        adjacency[b].add(a)
    component: dict[str, int] = {}
    number = 0
    for bus in (b["id"] for b in buses):
        if bus in component:
            continue
        number += 1
        queue = deque([bus])
        component[bus] = number
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in component:
                    component[neighbor] = number
                    queue.append(neighbor)
    return component


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the public-data Maryland nodal PCM ModelCase.")
    parser.add_argument("--endpoint-substation-km", type=float, default=3.0)
    args = parser.parse_args()

    osm_path = RAW_DIR / "osm_power_maryland_buffer.json"
    utility_path = RAW_DIR / "maryland_utility_polygons.geojson"
    for required in (osm_path, utility_path, MD100_DIR / "zonedata.csv", PJM_SOURCE_DIR / "gendata.csv"):
        if not required.exists():
            raise FileNotFoundError(required)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REF_DIR.mkdir(parents=True, exist_ok=True)
    osm = json.loads(osm_path.read_text(encoding="utf-8"))
    utility = json.loads(utility_path.read_text(encoding="utf-8"))
    lookup = build_utility_lookup(utility)

    substations: list[dict[str, Any]] = []
    for element in osm.get("elements", []):
        tags = element.get("tags") or {}
        if tags.get("power") != "substation":
            continue
        points = coords(element)
        voltages = parse_voltage(tags.get("voltage"))
        if not points or not voltages:
            continue
        lon = sum(p[0] for p in points) / len(points)
        lat = sum(p[1] for p in points) / len(points)
        location = lookup(lon, lat)
        for kv in voltages:
            substations.append(
                {
                    "id": f"OSM_S{element['id']}_{kv}",
                    "osm_id": int(element["id"]),
                    "kv": kv,
                    "lon": lon,
                    "lat": lat,
                    "zone": location[1] if location else "EXT",
                    "utility": location[0] if location else "Outside Maryland utility polygons",
                    "kind": "substation",
                    "name": tags.get("name", ""),
                }
            )

    buses_by_id = {bus["id"]: bus for bus in substations}
    junctions: dict[tuple[int, float, float], dict[str, Any]] = {}
    branches: list[dict[str, Any]] = []
    branch_provenance: list[dict[str, Any]] = []

    def endpoint_bus(point: tuple[float, float], kv: int) -> dict[str, Any]:
        nearest = nearest_bus(point[0], point[1], kv, substations, args.endpoint_substation_km)
        if nearest is not None:
            return nearest
        key = (kv, round(point[0], 5), round(point[1], 5))
        if key not in junctions:
            location = lookup(point[0], point[1])
            junctions[key] = {
                "id": f"OSM_J{kv}_{key[2]:.5f}_{key[1]:.5f}".replace("-", "m").replace(".", "p"),
                "osm_id": "",
                "kv": kv,
                "lon": point[0],
                "lat": point[1],
                "zone": location[1] if location else "EXT",
                "utility": location[0] if location else "Outside Maryland utility polygons",
                "kind": "junction",
                "name": "",
            }
        return junctions[key]

    for element in osm.get("elements", []):
        tags = element.get("tags") or {}
        if tags.get("power") not in {"line", "cable"}:
            continue
        points = coords(element)
        voltages = parse_voltage(tags.get("voltage"))
        if len(points) < 2 or not voltages:
            continue
        sample = [points[0], points[len(points) // 2], points[-1]]
        if not any(lookup(lon, lat) for lon, lat in sample):
            continue
        kv = max(voltages)
        a, b = endpoint_bus(points[0], kv), endpoint_bus(points[-1], kv)
        if a["id"] == b["id"]:
            continue
        ncircuits = circuits(tags)
        length = max(0.05, line_length_km(points))
        x_pu = max(1.0e-5, 0.4 * length * 100.0 / (kv * kv) / ncircuits)
        rating = RATING_MW[kv] * ncircuits
        branch_id = f"OSM_L{element['id']}"
        branches.append(
            {
                "branch_id": branch_id,
                "from_bus": a["id"],
                "to_bus": b["id"],
                "x": x_pu,
                "rating": rating,
                "loss": 0.0,
                "kind": tags.get("power"),
            }
        )
        branch_provenance.append(
            {
                "Branch_ID": branch_id,
                "Source": "OpenStreetMap",
                "OSM_way_id": int(element["id"]),
                "Voltage_kV": kv,
                "Circuits": ncircuits,
                "Length_km": length,
                "Electrical_parameters": "inferred",
                "Reactance_assumption": "0.4 ohm/km; 100 MVA base; divided by circuit count",
                "Rating_assumption": f"{RATING_MW[kv]:g} MW per circuit",
            }
        )

    buses_by_id.update({bus["id"]: bus for bus in junctions.values()})

    substation_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for bus in substations:
        substation_groups[bus["osm_id"]].append(bus)
    for osm_id, group in substation_groups.items():
        ordered = sorted(group, key=lambda bus: bus["kv"])
        for low, high in zip(ordered, ordered[1:]):
            branch_id = f"OSM_T{osm_id}_{low['kv']}_{high['kv']}"
            rating = min(RATING_MW[low["kv"]], RATING_MW[high["kv"]]) * 2
            branches.append(
                {
                    "branch_id": branch_id,
                    "from_bus": low["id"],
                    "to_bus": high["id"],
                    "x": 0.04,
                    "rating": rating,
                    "loss": 0.0,
                    "kind": "inferred_transformer",
                }
            )
            branch_provenance.append(
                {
                    "Branch_ID": branch_id,
                    "Source": "inferred from multi-voltage OSM substation",
                    "OSM_way_id": "",
                    "Voltage_kV": f"{low['kv']}/{high['kv']}",
                    "Circuits": "",
                    "Length_km": 0.0,
                    "Electrical_parameters": "inferred",
                    "Reactance_assumption": "0.04 pu transformer proxy",
                    "Rating_assumption": "twice lower-voltage line proxy",
                }
            )

    used_bus_ids = {branch["from_bus"] for branch in branches} | {branch["to_bus"] for branch in branches}
    buses = [buses_by_id[bus_id] for bus_id in sorted(used_bus_ids)]
    components = connected_components(buses, branches)

    load_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for bus in buses:
        if bus["zone"] in ZONE_PEAKS and bus["kind"] == "substation":
            load_candidates[bus["zone"]].append(bus)
    for zone in ZONE_PEAKS:
        if not load_candidates[zone]:
            load_candidates[zone] = [b for b in buses if b["zone"] == zone]
        if not load_candidates[zone]:
            raise RuntimeError(f"No retained buses in Maryland zone {zone}")

    weights: dict[str, float] = {bus["id"]: 0.0 for bus in buses}
    for zone, candidates in load_candidates.items():
        raw = {bus["id"]: math.sqrt(bus["kv"]) for bus in candidates}
        denominator = sum(raw.values())
        for bus_id, value in raw.items():
            weights[bus_id] = value / denominator

    bus_frame = pd.DataFrame(
        [
            {
                "Bus_id": bus["id"],
                "Zone_id": bus["zone"],
                "LoadZone": bus["zone"],
                "State": "MD" if bus["zone"] != "EXT" else "EXT",
                "Latitude": bus["lat"],
                "Longitude": bus["lon"],
                "Load_share": weights[bus["id"]],
                "Demand (MW)": ZONE_PEAKS.get(bus["zone"], 0.0) * weights[bus["id"]],
            }
            for bus in buses
        ]
    )
    write_csv(bus_frame, DATA_DIR / "busdata.csv")

    branch_frame = pd.DataFrame(
        [
            {
                "From_zone": buses_by_id[b["from_bus"]]["zone"],
                "To_zone": buses_by_id[b["to_bus"]]["zone"],
                "from_bus": b["from_bus"],
                "to_bus": b["to_bus"],
                "X": b["x"],
                "Forward Capacity (MW)": b["rating"],
                "Reverse Capacity (MW)": b["rating"],
                "Loss (%)": b["loss"],
            }
            for b in branches
        ]
    )
    write_csv(branch_frame, DATA_DIR / "branchdata.csv")

    zonedata = pd.DataFrame(
        [{"Zone_id": zone, "Demand (MW)": peak, "State": "MD"} for zone, peak in ZONE_PEAKS.items()]
        + [{"Zone_id": "EXT", "Demand (MW)": 0.0, "State": "EXT"}]
    )
    write_csv(zonedata, DATA_DIR / "zonedata.csv")

    zonal_pairs = branch_frame.groupby(["From_zone", "To_zone"], as_index=False).agg(
        {"Forward Capacity (MW)": "sum", "Reverse Capacity (MW)": "sum"}
    )
    zonal_pairs["X"] = 0.01
    zonal_pairs["Loss (%)"] = 0.0
    write_csv(
        zonal_pairs[["From_zone", "To_zone", "X", "Forward Capacity (MW)", "Reverse Capacity (MW)", "Loss (%)"]],
        DATA_DIR / "linedata.csv",
    )

    source_gen = pd.read_csv(PJM_SOURCE_DIR / "gendata.csv")
    generators = source_gen[source_gen["State"].eq("MD")].copy()
    assignments = [choose_gen_bus(row, buses) for _, row in generators.iterrows()]
    generators["Bus_id"] = [bus["id"] for bus in assignments]
    generators["LoadZone"] = [bus["zone"] for bus in assignments]
    generators["Zone"] = [bus["zone"] for bus in assignments]
    write_csv(generators, DATA_DIR / "gendata.csv")

    storage = pd.read_csv(PJM_SOURCE_DIR / "storagedata.csv")
    storage = storage[storage["State"].eq("MD")].copy()
    if len(storage):
        storage_assignments = [choose_gen_bus(row, buses) for _, row in storage.iterrows()]
        storage["Bus_id"] = [bus["id"] for bus in storage_assignments]
        storage["LoadZone"] = [bus["zone"] for bus in storage_assignments]
        storage["Zone"] = [bus["zone"] for bus in storage_assignments]
    else:
        storage["Bus_id"] = pd.Series(dtype=str)
        storage["LoadZone"] = pd.Series(dtype=str)
    write_csv(storage, DATA_DIR / "storagedata.csv")

    load_source = time_window(pd.read_csv(MD100_DIR / "load_timeseries_regional.csv"))
    time_cols = ["Time Period", "Month", "Day", "Hours"]
    regional = load_source[time_cols].copy()
    for zone in ZONE_PEAKS:
        source_col = {"APS_MD": "AP_MD", "BGE": "BC_MD", "DPL_MD": "DPL_MD", "PEPCO": "PEP_MD"}[zone]
        regional[zone] = load_source[source_col].values
    regional["EXT"] = 0.0
    hourly_load = sum(regional[zone] * peak for zone, peak in ZONE_PEAKS.items())
    regional["NI"] = 0.55 * hourly_load
    write_csv(regional, DATA_DIR / "load_timeseries_regional.csv")

    nodal_load = regional[time_cols].copy()
    for bus in buses:
        nodal_load[bus["id"]] = regional[bus["zone"]].values if bus["zone"] in ZONE_PEAKS else 0.0
    write_csv(nodal_load, DATA_DIR / "load_timeseries_nodal.csv")

    boundary_ids = sorted(
        {
            b["from_bus"] if buses_by_id[b["from_bus"]]["zone"] == "EXT" else b["to_bus"]
            for b in branches
            if (buses_by_id[b["from_bus"]]["zone"] == "EXT") != (buses_by_id[b["to_bus"]]["zone"] == "EXT")
        }
    )
    if not boundary_ids:
        raise RuntimeError("No Maryland/external boundary buses were retained")
    boundary_weight = {bus_id: 1.0 / len(boundary_ids) for bus_id in boundary_ids}
    ni_target = regional[time_cols].copy()
    ni_cap = regional[time_cols].copy()
    for bus in buses:
        weight = boundary_weight.get(bus["id"], 0.0)
        ni_target[bus["id"]] = regional["NI"] * weight
        ni_cap[bus["id"]] = hourly_load * weight
    write_csv(ni_target, DATA_DIR / "ni_timeseries_nodal_target.csv")
    write_csv(ni_cap, DATA_DIR / "ni_timeseries_nodal_cap.csv")

    for output_name, source_name in (("solar_timeseries_regional.csv", "solar_timeseries_regional.csv"), ("wind_timeseries_regional.csv", "wind_timeseries_regional.csv")):
        source = time_window(pd.read_csv(PJM_SOURCE_DIR / source_name))
        output = source[time_cols].copy()
        for zone, source_zone in SOURCE_ZONE.items():
            output[zone] = source[source_zone].values
        output["EXT"] = 0.0
        write_csv(output, DATA_DIR / output_name)

    af_source = time_window(pd.read_csv(PJM_SOURCE_DIR / "gen_availability_timeseries.csv"))
    af_columns = time_cols + [column for column in generators["GeneratorID"].astype(str) if column in af_source.columns]
    write_csv(af_source[af_columns], DATA_DIR / "gen_availability_timeseries.csv")

    shutil.copyfile(MD100_DIR / "single_parameter.csv", DATA_DIR / "single_parameter.csv")
    pd.DataFrame(
        [
            {"State": "MD", "Time Period": 1, "Allowance (tons)": 1.0e12},
            {"State": "EXT", "Time Period": 1, "Allowance (tons)": 1.0e12},
        ]
    ).to_csv(DATA_DIR / "carbonpolicies.csv", index=False, lineterminator="\n")
    pd.DataFrame(
        [
            {"From_state": "MD", "To_state": "EXT", "RPS": 0.0},
            {"From_state": "EXT", "To_state": "MD", "RPS": 0.0},
        ]
    ).to_csv(DATA_DIR / "rpspolicies.csv", index=False, lineterminator="\n")

    bus_reference = pd.DataFrame(
        [
            {
                "Bus_id": bus["id"],
                "OSM_element_id": bus["osm_id"],
                "Bus_kind": bus["kind"],
                "Voltage_kV": bus["kv"],
                "Name": bus["name"],
                "Utility_polygon": bus["utility"],
                "Zone_id": bus["zone"],
                "Component": components[bus["id"]],
            }
            for bus in buses
        ]
    )
    write_csv(bus_reference, REF_DIR / "bus_provenance.csv")
    write_csv(pd.DataFrame(branch_provenance), REF_DIR / "branch_provenance.csv")
    write_csv(
        pd.DataFrame(
            [
                {
                    "GeneratorID": row["GeneratorID"],
                    "PlantName": row["PlantName"],
                    "Bus_id": bus["id"],
                    "Distance_km": haversine_km(
                        (float(row["Longitude"]), float(row["Latitude"])), (bus["lon"], bus["lat"])
                    ),
                    "Assignment_rule": "nearest retained substation in source utility zone with size-based voltage preference",
                }
                for (_, row), bus in zip(generators.iterrows(), assignments)
            ]
        ),
        REF_DIR / "generator_bus_mapping.csv",
    )

    component_sizes = pd.Series(components).value_counts().sort_index()
    validation = {
        "case": CASE_DIR.name,
        "hours": len(regional),
        "buses": len(buses),
        "branches": len(branches),
        "substation_buses": sum(bus["kind"] == "substation" for bus in buses),
        "junction_buses": sum(bus["kind"] == "junction" for bus in buses),
        "connected_components": len(component_sizes),
        "component_bus_counts": {str(k): int(v) for k, v in component_sizes.items()},
        "boundary_buses": len(boundary_ids),
        "generators": len(generators),
        "generator_capacity_mw": float(generators["Pmax (MW)"].sum()),
        "peak_load_mw": sum(ZONE_PEAKS.values()),
        "zones": {zone: int(sum(bus["zone"] == zone for bus in buses)) for zone in [*ZONE_PEAKS, "EXT"]},
        "assumption_flags": [
            "OSM is a public-data reconstruction, not an official PJM network model",
            "line reactance and thermal ratings are inferred by voltage and geometry",
            "transformers are inferred at multi-voltage substations",
            "utility service territories assign Maryland planning zones",
            "NI target is 55% of modeled hourly load; flexible cap is 100%",
        ],
    }
    (REF_DIR / "build_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
