"""Apply curation and tested runtime calibration to the Maryland ModelCase."""

from __future__ import annotations

import json

import pandas as pd

import finalize_md_transmission_case as finalizer


if __name__ == "__main__":
    original_dumps = finalizer.json.dumps

    def normalized_dumps(value, **kwargs):
        kwargs.setdefault(
            "default",
            lambda item: item.item() if hasattr(item, "item") else str(item),
        )
        return original_dumps(value, **kwargs)

    finalizer.json.dumps = normalized_dumps
    finalizer.main()

    data_dir = finalizer.DATA_DIR
    reference_dir = finalizer.REF_DIR
    bus_path = data_dir / "busdata.csv"
    branch_path = data_dir / "branchdata.csv"
    branch_ref_path = reference_dir / "branch_provenance.csv"
    regional_path = data_dir / "load_timeseries_regional.csv"

    bus = pd.read_csv(bus_path)
    external = bus.index[bus["Zone_id"] == "EXT"]
    if external.empty:
        raise RuntimeError("Curated case has no EXT boundary buses")
    bus.loc[external, "Load_share"] = 1.0 / len(external)
    bus.to_csv(bus_path, index=False, lineterminator="\n")

    branch = pd.read_csv(branch_path)
    branch_ref = pd.read_csv(branch_ref_path)
    if len(branch) != len(branch_ref):
        raise RuntimeError("Branch table and provenance rows are not aligned")
    transformer = branch_ref["Source"].eq("inferred from multi-voltage OSM substation")
    multiplier = pd.Series(5.0, index=branch.index)
    multiplier.loc[transformer] = 25.0
    branch["Forward Capacity (MW)"] *= multiplier
    branch["Reverse Capacity (MW)"] *= multiplier
    branch_ref["Applied_capacity_multiplier"] = multiplier
    branch_ref["Case_capacity_MW"] = branch["Forward Capacity (MW)"]
    branch.to_csv(branch_path, index=False, lineterminator="\n")
    branch_ref.to_csv(branch_ref_path, index=False, lineterminator="\n")

    regional = pd.read_csv(regional_path)
    regional["NI"] = 0.0
    regional.to_csv(regional_path, index=False, lineterminator="\n")
    time_columns = ["Time Period", "Month", "Day", "Hours"]
    target = regional[time_columns].copy()
    for bus_id in bus["Bus_id"].astype(str):
        target[bus_id] = 0.0
    target.to_csv(data_dir / "ni_timeseries_nodal_target.csv", index=False, lineterminator="\n")

    cross = branch[branch["From_zone"].eq("EXT") ^ branch["To_zone"].eq("EXT")].copy()
    cross["ext_bus"] = cross.apply(
        lambda row: row["from_bus"] if row["From_zone"] == "EXT" else row["to_bus"], axis=1
    )
    interface_capacity = cross.groupby("ext_bus")["Forward Capacity (MW)"].sum()
    weights = (interface_capacity / interface_capacity.sum()).to_dict()
    hourly_load = sum(regional[zone] * peak for zone, peak in finalizer.ZONE_PEAKS.items())
    cap_values = {
        bus_id: hourly_load * weights.get(bus_id, 0.0)
        for bus_id in bus["Bus_id"].astype(str)
    }
    cap = pd.concat([regional[time_columns], pd.DataFrame(cap_values)], axis=1)
    cap.to_csv(data_dir / "ni_timeseries_nodal_cap.csv", index=False, lineterminator="\n")

    validation_path = reference_dir / "build_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["network_calibration"] = {
        "osm_corridor_capacity_multiplier": 5.0,
        "inferred_transformer_capacity_multiplier": 25.0,
        "purpose": "compensate for incomplete parallel-circuit and transformer detail in OSM",
    }
    validation["interchange_assumption"] = {
        "target": "0 MW; no authoritative schedule assumed",
        "cap": "hourly system load allocated by retained boundary-interface capacity",
    }
    validation["assumption_flags"] = [
        flag for flag in validation["assumption_flags"] if "NI target is 55%" not in flag
    ] + [
        "NI target is zero; imports are endogenous within capacity-weighted boundary caps",
        "ratings include documented benchmark calibration multipliers",
    ]
    validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
