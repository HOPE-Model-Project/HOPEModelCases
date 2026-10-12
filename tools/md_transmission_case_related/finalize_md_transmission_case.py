from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd


TOOLS_DIR = Path(__file__).resolve().parent
MODELCASES_DIR = TOOLS_DIR.parents[1]
CASE_DIR = MODELCASES_DIR / "MD_PCM_transmission_public_case"
DATA_DIR = CASE_DIR / "Data_MD_PCM_transmission_public"
REF_DIR = CASE_DIR / "references"
TIME_COLUMNS = ["Time Period", "Month", "Day", "Hours"]
ZONE_PEAKS = {"APS_MD": 2326.75, "BGE": 6520.0, "DPL_MD": 818.5, "PEPCO": 10097.9}


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(h)))


def components(bus_ids: list[str], branch: pd.DataFrame) -> dict[str, int]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for row in branch.itertuples(index=False):
        a, b = str(row.from_bus), str(row.to_bus)
        adjacency[a].add(b)
        adjacency[b].add(a)
    result: dict[str, int] = {}
    number = 0
    for bus in bus_ids:
        if bus in result:
            continue
        number += 1
        result[bus] = number
        queue = deque([bus])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor not in result:
                    result[neighbor] = number
                    queue.append(neighbor)
    return result


def main() -> None:
    bus = pd.read_csv(DATA_DIR / "busdata.csv")
    branch = pd.read_csv(DATA_DIR / "branchdata.csv")
    bus_ref = pd.read_csv(REF_DIR / "bus_provenance.csv")
    branch_ref = pd.read_csv(REF_DIR / "branch_provenance.csv")
    if len(branch_ref) != len(branch):
        raise RuntimeError("Branch table/provenance row counts do not align before curation")

    component_sizes = bus_ref.groupby("Component").size()
    retained_components = component_sizes[component_sizes >= 100].index.tolist()
    if len(retained_components) != 2:
        raise RuntimeError(f"Expected mainland and Eastern Shore components; found {retained_components}")
    retained = set(bus_ref.loc[bus_ref["Component"].isin(retained_components), "Bus_id"].astype(str))
    keep_branch = branch["from_bus"].astype(str).isin(retained) & branch["to_bus"].astype(str).isin(retained)
    branch = branch.loc[keep_branch].reset_index(drop=True)
    branch_ref = branch_ref.loc[keep_branch.values].reset_index(drop=True)
    bus = bus[bus["Bus_id"].astype(str).isin(retained)].reset_index(drop=True)
    bus_ref = bus_ref[bus_ref["Bus_id"].astype(str).isin(retained)].reset_index(drop=True)

    combined = bus_ref.merge(bus[["Bus_id", "Latitude", "Longitude"]], on="Bus_id")
    external_by_component = {
        component: combined[(combined["Component"] == component) & (combined["Zone_id"] == "EXT")]
        for component in retained_components
    }
    if any(frame.empty for frame in external_by_component.values()):
        raise RuntimeError("Both retained components require an external boundary bus")
    left, right = retained_components
    choices = [
        (haversine_km((a.Longitude, a.Latitude), (b.Longitude, b.Latitude)), a.Bus_id, b.Bus_id)
        for a in external_by_component[left].itertuples(index=False)
        for b in external_by_component[right].itertuples(index=False)
    ]
    distance, from_bus, to_bus = min(choices)
    proxy_x = max(1.0e-5, 0.4 * distance * 100.0 / (230.0 * 230.0))
    branch.loc[len(branch)] = {
        "From_zone": "EXT",
        "To_zone": "EXT",
        "from_bus": from_bus,
        "to_bus": to_bus,
        "X": proxy_x,
        "Forward Capacity (MW)": 1200.0,
        "Reverse Capacity (MW)": 1200.0,
        "Loss (%)": 0.0,
    }
    branch_ref.loc[len(branch_ref)] = {
        "Branch_ID": "PROXY_PJM_MAINLAND_EASTERN_SHORE",
        "Source": "modeling assumption",
        "OSM_way_id": "",
        "Voltage_kV": 230,
        "Circuits": 2,
        "Length_km": distance,
        "Electrical_parameters": "inferred external-PJM corridor proxy",
        "Reactance_assumption": "0.4 ohm/km; 100 MVA base",
        "Rating_assumption": "1200 MW bidirectional proxy",
    }

    bus["Load_share"] = 0.0
    bus["Demand (MW)"] = 0.0
    for zone, peak in ZONE_PEAKS.items():
        candidates = bus[(bus["Zone_id"] == zone) & bus["Bus_id"].isin(bus_ref.loc[bus_ref["Bus_kind"] == "substation", "Bus_id"])]
        if candidates.empty:
            candidates = bus[bus["Zone_id"] == zone]
        raw = candidates["Bus_id"].map(dict(zip(bus_ref["Bus_id"], bus_ref["Voltage_kV"]))).astype(float).pow(0.5)
        shares = raw / raw.sum()
        bus.loc[candidates.index, "Load_share"] = shares.values
        bus.loc[candidates.index, "Demand (MW)"] = shares.values * peak

    retained_order = bus["Bus_id"].astype(str).tolist()
    for filename in ("load_timeseries_nodal.csv",):
        frame = pd.read_csv(DATA_DIR / filename)
        frame[TIME_COLUMNS + retained_order].to_csv(DATA_DIR / filename, index=False, lineterminator="\n")

    regional = pd.read_csv(DATA_DIR / "load_timeseries_regional.csv")
    hourly_load = sum(regional[zone] * peak for zone, peak in ZONE_PEAKS.items())
    boundary = sorted(
        {
            str(row.from_bus) if row.From_zone == "EXT" else str(row.to_bus)
            for row in branch.itertuples(index=False)
            if (row.From_zone == "EXT") != (row.To_zone == "EXT")
        }
    )
    if not boundary:
        raise RuntimeError("No external boundary buses remain after curation")
    weights = {bus_id: 1.0 / len(boundary) for bus_id in boundary}
    for filename, total in (
        ("ni_timeseries_nodal_target.csv", 0.55 * hourly_load),
        ("ni_timeseries_nodal_cap.csv", hourly_load),
    ):
        frame = regional[TIME_COLUMNS].copy()
        values = {bus_id: total * weights.get(bus_id, 0.0) for bus_id in retained_order}
        frame = pd.concat([frame, pd.DataFrame(values)], axis=1)
        frame.to_csv(DATA_DIR / filename, index=False, lineterminator="\n")

    generators = pd.read_csv(DATA_DIR / "gendata.csv")
    retained_substations = combined[combined["Bus_kind"] == "substation"].copy()
    retained_bus_ids = set(retained_order)
    mapping_rows = []
    for index, row in generators.iterrows():
        zone = str(row["Zone"])
        candidates = retained_substations[retained_substations["Zone_id"] == zone]
        if candidates.empty:
            candidates = retained_substations[retained_substations["Zone_id"] != "EXT"]
        if str(row["Bus_id"]) not in retained_bus_ids:
            best = min(
                candidates.itertuples(index=False),
                key=lambda candidate: haversine_km(
                    (float(row["Longitude"]), float(row["Latitude"])),
                    (float(candidate.Longitude), float(candidate.Latitude)),
                ),
            )
            generators.at[index, "Bus_id"] = best.Bus_id
            generators.at[index, "Zone"] = best.Zone_id
            generators.at[index, "LoadZone"] = best.Zone_id
        selected = combined[combined["Bus_id"] == generators.at[index, "Bus_id"]].iloc[0]
        mapping_rows.append(
            {
                "GeneratorID": row["GeneratorID"],
                "PlantName": row["PlantName"],
                "Bus_id": selected["Bus_id"],
                "Distance_km": haversine_km(
                    (float(row["Longitude"]), float(row["Latitude"])),
                    (float(selected["Longitude"]), float(selected["Latitude"])),
                ),
                "Assignment_rule": "nearest retained substation in source utility zone with curation remap",
            }
        )

    final_components = components(retained_order, branch)
    bus_ref["Component"] = bus_ref["Bus_id"].astype(str).map(final_components)
    if len(set(final_components.values())) != 1:
        raise RuntimeError("Curated network is not connected")

    bus.to_csv(DATA_DIR / "busdata.csv", index=False, lineterminator="\n")
    branch.to_csv(DATA_DIR / "branchdata.csv", index=False, lineterminator="\n")
    generators.to_csv(DATA_DIR / "gendata.csv", index=False, lineterminator="\n")
    bus_ref.to_csv(REF_DIR / "bus_provenance.csv", index=False, lineterminator="\n")
    branch_ref.to_csv(REF_DIR / "branch_provenance.csv", index=False, lineterminator="\n")
    pd.DataFrame(mapping_rows).to_csv(REF_DIR / "generator_bus_mapping.csv", index=False, lineterminator="\n")

    validation = {
        "case": CASE_DIR.name,
        "hours": len(regional),
        "buses": len(bus),
        "branches": len(branch),
        "connected_components": 1,
        "retained_raw_components": [int(value) for value in retained_components],
        "discarded_orphan_buses": int(component_sizes[~component_sizes.index.isin(retained_components)].sum()),
        "boundary_buses": len(boundary),
        "generators": len(generators),
        "generator_capacity_mw": float(generators["Pmax (MW)"].sum()),
        "peak_load_mw": sum(ZONE_PEAKS.values()),
        "zones": bus.groupby("Zone_id").size().astype(int).to_dict(),
        "external_corridor_proxy": {
            "from_bus": from_bus,
            "to_bus": to_bus,
            "distance_km": distance,
            "capacity_mw": 1200.0,
        },
        "checks": {
            "all_branch_endpoints_exist": bool(
                branch["from_bus"].astype(str).isin(retained_bus_ids).all()
                and branch["to_bus"].astype(str).isin(retained_bus_ids).all()
            ),
            "all_generators_mapped": bool(generators["Bus_id"].astype(str).isin(retained_bus_ids).all()),
            "zone_peak_loads_preserved": {
                zone: abs(bus.loc[bus["Zone_id"] == zone, "Demand (MW)"].sum() - peak) < 1.0e-6
                for zone, peak in ZONE_PEAKS.items()
            },
        },
        "assumption_flags": [
            "OSM is a public-data reconstruction, not an official PJM network model",
            "line reactance and thermal ratings are inferred by voltage and geometry",
            "tiny disconnected OSM fragments are excluded",
            "mainland and Eastern Shore are joined by a transparent external-PJM corridor proxy",
            "NI target is 55% of modeled hourly load; flexible cap is 100%",
        ],
    }
    (REF_DIR / "build_validation.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
