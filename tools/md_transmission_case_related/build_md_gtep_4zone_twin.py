"""Build an aggregated Maryland GTEP case paired to the public nodal PCM case."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from build_md_gtep_nodal_twin import (
    PCM_CASE,
    PCM_DATA,
    TIME_COLUMNS,
    build_generation_candidates,
    build_generator_availability,
    build_storage_candidates,
    representative_week,
    select_candidate_buses,
    stable_ids,
)


ROOT = Path(__file__).resolve().parents[2]
CASE = ROOT / "MD_GTEP_4zone_public_case"
DATA = CASE / "Data_MD_GTEP_4zone_public"
REFERENCES = CASE / "references"


def write_csv(frame: pd.DataFrame, name: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATA / name, index=False)


def build() -> None:
    generators, branches, _ = stable_ids()
    buses = pd.read_csv(PCM_DATA / "busdata.csv")
    zones = pd.read_csv(PCM_DATA / "zonedata.csv")
    regional_load = representative_week(
        pd.read_csv(PCM_DATA / "load_timeseries_regional.csv")
    )
    regional_solar = representative_week(
        pd.read_csv(PCM_DATA / "solar_timeseries_regional.csv")
    )
    regional_wind = representative_week(
        pd.read_csv(PCM_DATA / "wind_timeseries_regional.csv")
    )

    area_map = {zone: index + 1 for index, zone in enumerate(zones["Zone_id"])}
    zones["Area"] = zones["Zone_id"].map(area_map)
    zones["Flag_MD"] = (zones["State"].astype(str) == "MD").astype(int)
    write_csv(zones, "zonedata.csv")
    write_csv(regional_load, "load_timeseries_regional.csv")
    write_csv(regional_solar, "solar_timeseries_regional.csv")
    write_csv(regional_wind, "wind_timeseries_regional.csv")

    gtep_generators = generators.copy()
    gtep_generators["Planning_Zone"] = gtep_generators["Zone"].astype(str)
    write_csv(gtep_generators, "gendata.csv")

    storage = pd.read_csv(PCM_DATA / "storagedata.csv")
    if not storage.empty:
        storage["Asset_ID"] = storage["StorageID"].astype(str)
        storage["Planning_Zone"] = storage["Zone"].astype(str)
    write_csv(storage, "storagedata.csv")
    write_csv(pd.read_csv(PCM_DATA / "linedata.csv"), "linedata.csv")

    candidate_buses = select_candidate_buses(generators, buses)
    generation_candidates = build_generation_candidates(candidate_buses)
    storage_candidates = build_storage_candidates(candidate_buses)
    generation_candidates["Zone"] = generation_candidates["Planning_Zone"]
    storage_candidates["Zone"] = storage_candidates["Planning_Zone"]
    write_csv(generation_candidates, "gendata_candidate.csv")
    write_csv(storage_candidates, "storagedata_candidate.csv")

    cross_zone = branches[
        branches["From_zone"].astype(str) != branches["To_zone"].astype(str)
    ].sort_values("Forward Capacity (MW)", ascending=False)
    line_candidates = pd.DataFrame(
        [
            {
                "From_zone": branch["From_zone"],
                "To_zone": branch["To_zone"],
                "X": branch["X"],
                "Forward Capacity (MW)": 1000.0,
                "Reverse Capacity (MW)": 1000.0,
                "Cost (M$)": 250.0,
                "Loss (%)": 0.0,
                "Corridor_ID": branch["Corridor_ID"],
                "PCM_from_bus": branch["from_bus"],
                "PCM_to_bus": branch["to_bus"],
            }
            for _, branch in cross_zone.head(4).iterrows()
        ]
    )
    write_csv(line_candidates, "linedata_candidate.csv")

    availability = build_generator_availability(
        gtep_generators,
        generation_candidates,
        regional_solar,
        regional_wind,
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

    REFERENCES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "Planning_Zone": zone,
                "Candidate_Bus": bus,
                "Rule": "largest_existing_generation_bus",
            }
            for zone, bus in candidate_buses.items()
        ]
    ).to_csv(REFERENCES / "candidate_bus_mapping.csv", index=False)
    validation = {
        "planning_zones": int(len(zones)),
        "zonal_corridors": int(len(pd.read_csv(PCM_DATA / "linedata.csv"))),
        "physical_pcm_buses": int(len(buses)),
        "physical_pcm_branches": int(len(branches)),
        "existing_generators": int(len(generators)),
        "generation_candidates": int(len(generation_candidates)),
        "storage_candidates": int(len(storage_candidates)),
        "branch_specific_line_candidates": int(len(line_candidates)),
        "hours": int(len(regional_load)),
        "candidate_buses": candidate_buses,
        "source_pcm_case": PCM_CASE.name,
    }
    (REFERENCES / "build_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
