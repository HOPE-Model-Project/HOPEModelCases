"""Build the bus-resolved Maryland GTEP twin from the public Maryland PCM case."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PCM_CASE = ROOT / "MD_PCM_transmission_public_case"
PCM_DATA = PCM_CASE / "Data_MD_PCM_transmission_public"
GTEP_CASE = ROOT / "MD_GTEP_transmission_public_case"
GTEP_DATA = GTEP_CASE / "Data_MD_GTEP_transmission_public"
GTEP_SETTINGS = GTEP_CASE / "Settings"
GTEP_REFERENCES = GTEP_CASE / "references"

TIME_COLUMNS = ["Time Period", "Month", "Day", "Hours"]


def write_csv(frame: pd.DataFrame, name: str) -> None:
    GTEP_DATA.mkdir(parents=True, exist_ok=True)
    frame.to_csv(GTEP_DATA / name, index=False)


def stable_ids() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    generators = pd.read_csv(PCM_DATA / "gendata.csv")
    branches = pd.read_csv(PCM_DATA / "branchdata.csv")
    provenance = pd.read_csv(PCM_CASE / "references" / "branch_provenance.csv")
    if len(branches) != len(provenance):
        raise ValueError("branchdata and branch_provenance row counts differ")
    generators["Asset_ID"] = generators["GeneratorID"].astype(str)
    if not generators["Asset_ID"].is_unique:
        raise ValueError("GeneratorID must be unique before it can serve as Asset_ID")
    branches["Corridor_ID"] = provenance["Branch_ID"].astype(str).to_numpy()
    if not branches["Corridor_ID"].is_unique:
        raise ValueError("Branch_ID must be unique before it can serve as Corridor_ID")
    generators.to_csv(PCM_DATA / "gendata.csv", index=False)
    branches.to_csv(PCM_DATA / "branchdata.csv", index=False)
    return generators, branches, provenance


def expand_profile_by_bus(
    source: pd.DataFrame, buses: pd.DataFrame, fill: float = 0.0
) -> pd.DataFrame:
    columns: dict[str, object] = {
        column: source[column].to_numpy() for column in TIME_COLUMNS
    }
    for row in buses.itertuples(index=False):
        bus = str(row.Bus_id)
        zone = str(row.Zone_id)
        columns[bus] = source[zone].to_numpy() if zone in source.columns else fill
    return pd.DataFrame(columns)


def representative_week(frame: pd.DataFrame) -> pd.DataFrame:
    if len(frame) != 168:
        raise ValueError(f"Expected a 168-hour source week; found {len(frame)} rows")
    result = frame.copy()
    result["Time Period"] = [day for day in range(1, 8) for _ in range(24)]
    result["Hours"] = list(range(1, 25)) * 7
    return result


def select_candidate_buses(
    generators: pd.DataFrame, buses: pd.DataFrame
) -> dict[str, str]:
    selected: dict[str, str] = {}
    internal_zones = sorted(z for z in buses["Zone_id"].astype(str).unique() if z != "EXT")
    for zone in internal_zones:
        local_generators = generators[generators["Zone"].astype(str) == zone]
        if not local_generators.empty:
            capacity = (
                local_generators.groupby("Bus_id", dropna=False)["Pmax (MW)"]
                .sum()
                .sort_values(ascending=False)
            )
            selected[zone] = str(capacity.index[0])
        else:
            local_buses = buses[buses["Zone_id"].astype(str) == zone]
            selected[zone] = str(
                local_buses.sort_values("Demand (MW)", ascending=False).iloc[0]["Bus_id"]
            )
    return selected


def build_generation_candidates(candidate_buses: dict[str, str]) -> pd.DataFrame:
    technologies = [
        {
            "Type": "NGCC",
            "Pmax (MW)": 5000.0,
            "Pmin (MW)": 0.0,
            "Cost ($/MW/yr)": 110000.0,
            "Cost ($/MWh)": 35.0,
            "Flag_thermal": 1,
            "Flag_VRE": 0,
            "EF": 0.37,
            "CC": 0.90,
            "AF": 1.0,
            "FOR": 0.05,
            "Flag_RPS": 0,
            "RM_SPIN": 0.10,
            "RU": 1.0,
            "RD": 1.0,
            "Flag_UC": 0,
            "Min_down_time": 0,
            "Min_up_time": 0,
            "Start_up_cost ($/MW)": 0.0,
        },
        {
            "Type": "SolarPV",
            "Pmax (MW)": 5000.0,
            "Pmin (MW)": 0.0,
            "Cost ($/MW/yr)": 70000.0,
            "Cost ($/MWh)": 0.0,
            "Flag_thermal": 0,
            "Flag_VRE": 1,
            "EF": 0.0,
            "CC": 0.25,
            "AF": 1.0,
            "FOR": 0.0,
            "Flag_RPS": 1,
            "RM_SPIN": 0.0,
            "RU": 1.0,
            "RD": 1.0,
            "Flag_UC": 0,
            "Min_down_time": 0,
            "Min_up_time": 0,
            "Start_up_cost ($/MW)": 0.0,
        },
        {
            "Type": "WindOn",
            "Pmax (MW)": 4000.0,
            "Pmin (MW)": 0.0,
            "Cost ($/MW/yr)": 95000.0,
            "Cost ($/MWh)": 0.0,
            "Flag_thermal": 0,
            "Flag_VRE": 1,
            "EF": 0.0,
            "CC": 0.15,
            "AF": 1.0,
            "FOR": 0.0,
            "Flag_RPS": 1,
            "RM_SPIN": 0.0,
            "RU": 1.0,
            "RD": 1.0,
            "Flag_UC": 0,
            "Min_down_time": 0,
            "Min_up_time": 0,
            "Start_up_cost ($/MW)": 0.0,
        },
    ]
    rows = []
    for planning_zone, bus in candidate_buses.items():
        for technology in technologies:
            row = dict(technology)
            row.update(
                {
                    "Zone": bus,
                    "Bus_id": bus,
                    "Planning_Zone": planning_zone,
                    "Candidate_ID": f"MD_{planning_zone}_{technology['Type']}_001",
                    "Operational_Template_ID": f"HOPE_{technology['Type']}_DEFAULT",
                    "Flag_mustrun": 0,
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_storage_candidates(candidate_buses: dict[str, str]) -> pd.DataFrame:
    rows = []
    for planning_zone, bus in candidate_buses.items():
        rows.append(
            {
                "Zone": bus,
                "Bus_id": bus,
                "Planning_Zone": planning_zone,
                "Candidate_ID": f"MD_{planning_zone}_Battery_001",
                "Operational_Template_ID": "HOPE_BATTERY_4H_DEFAULT",
                "Type": "Battery",
                "Capacity (MWh)": 8000.0,
                "Max Power (MW)": 2000.0,
                "Charging efficiency": 0.92,
                "Discharging efficiency": 0.92,
                "Cost ($/MW/yr)": 125000.0,
                "Cost ($/MWh)": 0.1,
                "EF": 0.0,
                "CC": 1.0,
                "Charging Rate": 1.0,
                "Discharging Rate": 1.0,
            }
        )
    return pd.DataFrame(rows)


def build_generator_availability(
    existing: pd.DataFrame,
    candidates: pd.DataFrame,
    solar: pd.DataFrame,
    wind: pd.DataFrame,
) -> pd.DataFrame:
    columns: dict[str, object] = {
        column: solar[column].to_numpy() for column in TIME_COLUMNS
    }
    combined = pd.concat([existing, candidates], ignore_index=True, sort=False)
    for index, row in combined.iterrows():
        generator_column = f"G{index + 1}"
        bus = str(row["Zone"])
        technology = str(row["Type"]).lower()
        if "solar" in technology:
            values = solar[bus]
        elif "wind" in technology:
            values = wind[bus]
        else:
            values = pd.Series(float(row.get("AF", 1.0)), index=solar.index)
        columns[generator_column] = values.clip(lower=0.0, upper=1.0).to_numpy()
    return pd.DataFrame(columns)


def build() -> None:
    generators, branches, provenance = stable_ids()
    buses = pd.read_csv(PCM_DATA / "busdata.csv")
    nodal_load = pd.read_csv(PCM_DATA / "load_timeseries_nodal.csv")
    regional_solar = pd.read_csv(PCM_DATA / "solar_timeseries_regional.csv")
    regional_wind = pd.read_csv(PCM_DATA / "wind_timeseries_regional.csv")
    regional_load = pd.read_csv(PCM_DATA / "load_timeseries_regional.csv")

    area_map = {zone: index + 1 for index, zone in enumerate(sorted(buses["Zone_id"].unique()))}
    zones = pd.DataFrame(
        {
            "Zone_id": buses["Bus_id"].astype(str),
            "Demand (MW)": buses["Demand (MW)"].astype(float),
            "Area": buses["Zone_id"].map(area_map),
            "Flag_MD": (buses["State"].astype(str) == "MD").astype(int),
            "State": buses["State"].astype(str),
            "Planning_Zone": buses["Zone_id"].astype(str),
        }
    )
    write_csv(zones, "zonedata.csv")

    load = representative_week(nodal_load)
    load["NI"] = regional_load["NI"].to_numpy() if "NI" in regional_load else 0.0
    write_csv(load, "load_timeseries_regional.csv")
    solar = representative_week(expand_profile_by_bus(regional_solar, buses))
    wind = representative_week(expand_profile_by_bus(regional_wind, buses))
    write_csv(solar, "solar_timeseries_regional.csv")
    write_csv(wind, "wind_timeseries_regional.csv")

    gtep_generators = generators.copy()
    gtep_generators["Planning_Zone"] = gtep_generators["Zone"].astype(str)
    gtep_generators["Zone"] = gtep_generators["Bus_id"].astype(str)
    write_csv(gtep_generators, "gendata.csv")

    storage = pd.read_csv(PCM_DATA / "storagedata.csv")
    if not storage.empty:
        storage["Asset_ID"] = storage["StorageID"].astype(str)
        storage["Planning_Zone"] = storage["Zone"].astype(str)
        storage["Zone"] = storage["Bus_id"].astype(str)
    write_csv(storage, "storagedata.csv")

    lines = branches[
        ["from_bus", "to_bus", "Forward Capacity (MW)", "Reverse Capacity (MW)", "Loss (%)", "Corridor_ID"]
    ].rename(columns={"from_bus": "From_zone", "to_bus": "To_zone"})
    write_csv(lines, "linedata.csv")

    candidate_buses = select_candidate_buses(generators, buses)
    generation_candidates = build_generation_candidates(candidate_buses)
    storage_candidates = build_storage_candidates(candidate_buses)
    write_csv(generation_candidates, "gendata_candidate.csv")
    write_csv(storage_candidates, "storagedata_candidate.csv")

    candidate_branch_rows = []
    for _, branch in branches.sort_values("Forward Capacity (MW)", ascending=False).head(4).iterrows():
        candidate_branch_rows.append(
            {
                "From_zone": branch["from_bus"],
                "To_zone": branch["to_bus"],
                "X": branch["X"],
                "Forward Capacity (MW)": 1000.0,
                "Reverse Capacity (MW)": 1000.0,
                "Cost (M$)": 250.0,
                "Loss (%)": 0.0,
                "Corridor_ID": branch["Corridor_ID"],
            }
        )
    line_candidates = pd.DataFrame(candidate_branch_rows)
    write_csv(line_candidates, "linedata_candidate.csv")

    availability = build_generator_availability(
        gtep_generators, generation_candidates, solar, wind
    )
    write_csv(availability, "gen_availability_timeseries.csv")

    states = sorted(zones["State"].astype(str).unique())
    write_csv(
        pd.DataFrame(
            [(state, 1, 1.0e12) for state in states],
            columns=["State", "Time Period", "Allowance (tons)"],
        ),
        "carbonpolicies.csv",
    )
    write_csv(
        pd.DataFrame(
            [(state, state, 0.0) for state in states],
            columns=["From_state", "To_state", "RPS"],
        ),
        "rpspolicies.csv",
    )
    write_csv(
        pd.DataFrame(
            [
                {
                    "VOLL": 100000.0,
                    "planning_reserve_margin": 0.15,
                    "BigM": 1.0e13,
                    "PT_RPS": 1.0e10,
                    "PT_emis": 1.0e10,
                    "Inv_bugt_gen": 1.0e16,
                    "Inv_bugt_line": 1.0e16,
                    "Inv_bugt_storage": 1.0e16,
                    "alpha_storage_anchor": 0.5,
                    "spin_requirement": 0.03,
                    "delta_spin": 1.0 / 6.0,
                }
            ]
        ),
        "single_parameter.csv",
    )
    write_csv(
        pd.DataFrame(
            {
                "Time Period": list(range(1, 8)),
                "Weight": [53.0, 52.0, 52.0, 52.0, 52.0, 52.0, 52.0],
            }
        ),
        "rep_period_weights.csv",
    )

    GTEP_REFERENCES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"Planning_Zone": zone, "Candidate_Bus": bus, "Rule": "largest_existing_generation_bus"}
            for zone, bus in candidate_buses.items()
        ]
    ).to_csv(GTEP_REFERENCES / "candidate_bus_mapping.csv", index=False)
    validation = {
        "buses": int(len(buses)),
        "branches": int(len(branches)),
        "existing_generators": int(len(generators)),
        "generation_candidates": int(len(generation_candidates)),
        "storage_candidates": int(len(storage_candidates)),
        "line_candidates": int(len(line_candidates)),
        "hours": int(len(load)),
        "candidate_buses": candidate_buses,
        "stable_asset_ids": bool(gtep_generators["Asset_ID"].is_unique),
        "stable_corridor_ids": bool(lines["Corridor_ID"].is_unique),
        "source_pcm_case": str(PCM_CASE.name),
    }
    (GTEP_REFERENCES / "build_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
