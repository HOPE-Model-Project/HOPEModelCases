"""Build the canonical full-year Maryland GTEP-to-PCM benchmark pair.

The spatial and physical basis comes from the validated 168-hour Maryland
20% RPS public-data pair:

* four Maryland planning zones plus an explicit external boundary in GTEP;
* a 656-bus, 838-branch OSM-derived transmission realization in PCM; and
* the version-1 strict physical-realization contract.

The annual normalized load, wind, and solar chronology comes from the retained
Maryland 8760-hour benchmark.  Nodal load multipliers and flexible nodal
interchange bounds are regenerated deterministically for all 8760 rows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MODELCASES = SCRIPT_DIR.parent.parent

SOURCE_GTEP = MODELCASES / "MD_GTEP_RPS20_4zone_public_case"
SOURCE_PCM = MODELCASES / "MD_PCM_RPS20_transmission_public_case"
CHRONOLOGY_DATA = (
    MODELCASES
    / "MD_GTEP_holistic_full8760_case_v20260406g"
    / "Data_100RPS"
)

TARGET_GTEP = MODELCASES / "MD_GTEP_RPS20_4zone_full8760_public_case"
TARGET_PCM = MODELCASES / "MD_PCM_RPS20_transmission_full8760_public_case"
GTEP_DATA_NAME = "Data_MD_GTEP_RPS20_4zone_full8760_public"
PCM_DATA_NAME = "Data_MD_PCM_RPS20_transmission_full8760_public"

TIME_COLUMNS = ["Time Period", "Month", "Day", "Hours"]
INTERNAL_ZONES = ["APS_MD", "BGE", "DPL_MD", "PEPCO"]
EXPECTED_HOURS = 8760
EXPECTED_BUSES = 656
EXPECTED_BRANCHES = 838
DELIVERABILITY_CORRIDOR = "OSM_L1528639488"
DELIVERABILITY_ORIGINAL_MW = 500.0
DELIVERABILITY_ADJUSTED_MW = 600.0


def copy_case_without_outputs(source: Path, target: Path) -> None:
    """Copy a case for an isolated run while excluding generated outputs."""
    excluded = {"output", "output_holistic", "plot_output", "backup", "debug_report"}

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in excluded
            or name.startswith("output_")
            or name.startswith("output_backup")
        }

    shutil.copytree(source, target, ignore=ignore)


def materialize_pcm_month_validation(root: Path, month: int) -> None:
    """Create an isolated annual-GTEP/monthly-PCM functional validation pair.

    The published cases remain 8760-hour inputs.  This helper is only a bounded-
    memory integration test for workstations that cannot construct the monolithic
    656-bus annual PCM model.
    """
    if month not in range(1, 13):
        raise ValueError("validation month must be in 1..12")
    if root.exists():
        raise FileExistsError(f"Validation root already exists: {root}")
    gtep_target = root / "gtep_case"
    pcm_target = root / "pcm_case"
    root.mkdir(parents=True)
    copy_case_without_outputs(TARGET_GTEP, gtep_target)
    copy_case_without_outputs(TARGET_PCM, pcm_target)

    pcm_data = pcm_target / PCM_DATA_NAME
    time_files = (
        "load_timeseries_regional.csv",
        "wind_timeseries_regional.csv",
        "solar_timeseries_regional.csv",
        "load_timeseries_nodal.csv",
        "ni_timeseries_nodal_target.csv",
        "ni_timeseries_nodal_cap.csv",
        "gen_availability_timeseries.csv",
    )
    row_count: int | None = None
    for filename in time_files:
        path = pcm_data / filename
        header, rows = read_csv(path)
        selected = [row for row in rows if int(row["Month"]) == month]
        if not selected:
            raise ValueError(f"No rows for month {month} in {path}")
        if row_count is None:
            row_count = len(selected)
        elif len(selected) != row_count:
            raise ValueError(f"Monthly chronology mismatch in {path}")
        write_csv(path, header, selected)

    write_text(
        root / "validation_slice.yml",
        f"""
schema_version: 1
purpose: bounded-memory functional validation of the published full-year pair
gtep_source: {TARGET_GTEP}
pcm_source: {TARGET_PCM}
gtep_hours: 8760
pcm_month: {month}
pcm_hours: {row_count}
production_benchmark: false
note: The published source cases remain full-year. This slice validates the annual
  GTEP solve, deterministic physical handoff, and detailed PCM formulation on one
  calendar month; it is not a substitute for the annual PCM result.
""",
    )
    write_text(
        root / "run_pair.jl",
        """
using HOPE

const ROOT = @__DIR__
const GTEP_CASE = joinpath(ROOT, "gtep_case")
const PCM_CASE = joinpath(ROOT, "pcm_case")

result = HOPE.run_hope_holistic(
    GTEP_CASE,
    PCM_CASE;
    solver_override = "gurobi",
)
report = HOPE.write_holistic_coverage_report(
    result,
    joinpath(PCM_CASE, "Settings", "HOPE_holistic_acceptance.yml");
    require_all = true,
)
println("Holistic coverage passed: ", report["all_passed"])
""",
    )
    print(f"Created validation pair at {root}")
    print(f"PCM validation month={month}; rows={row_count}")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Missing CSV header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, target)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_annual_regional_rows() -> dict[str, list[dict[str, str]]]:
    source_names = {
        "load_timeseries_regional.csv": [*INTERNAL_ZONES, "EXT", "NI"],
        "wind_timeseries_regional.csv": [*INTERNAL_ZONES, "EXT"],
        "solar_timeseries_regional.csv": [*INTERNAL_ZONES, "EXT"],
    }
    output: dict[str, list[dict[str, str]]] = {}
    expected_calendar: list[tuple[str, str, str]] | None = None

    for filename, value_columns in source_names.items():
        _, source_rows = read_csv(CHRONOLOGY_DATA / filename)
        if len(source_rows) != EXPECTED_HOURS:
            raise ValueError(
                f"{filename} has {len(source_rows)} rows; expected {EXPECTED_HOURS}"
            )

        rows: list[dict[str, str]] = []
        calendar: list[tuple[str, str, str]] = []
        for source in source_rows:
            hour = source.get("Period", source.get("Hours", ""))
            calendar.append((source["Month"], source["Day"], hour))
            row = {
                "Time Period": "1",
                "Month": source["Month"],
                "Day": source["Day"],
                "Hours": hour,
            }
            for zone in INTERNAL_ZONES:
                if zone not in source:
                    raise KeyError(f"{filename} is missing zone column {zone}")
                row[zone] = source[zone]
            row["EXT"] = "0.0"
            if "NI" in value_columns:
                # The detailed public case uses endogenous boundary interchange.
                row["NI"] = "0.0"
            rows.append(row)

        if expected_calendar is None:
            expected_calendar = calendar
        elif calendar != expected_calendar:
            raise ValueError(f"Calendar mismatch in {filename}")
        output[filename] = rows

    assert expected_calendar is not None
    if len(set(expected_calendar)) != EXPECTED_HOURS:
        raise ValueError("Annual chronology contains duplicate month/day/hour keys")
    if expected_calendar[0] != ("1", "1", "1"):
        raise ValueError(f"Unexpected first annual hour: {expected_calendar[0]}")
    if expected_calendar[-1] != ("12", "31", "24"):
        raise ValueError(f"Unexpected last annual hour: {expected_calendar[-1]}")
    return output


def write_annual_regional_files(
    annual: dict[str, list[dict[str, str]]],
    target_data: Path,
) -> None:
    for filename, rows in annual.items():
        value_columns = [*INTERNAL_ZONES, "EXT"]
        if filename == "load_timeseries_regional.csv":
            value_columns.append("NI")
        write_csv(target_data / filename, [*TIME_COLUMNS, *value_columns], rows)


def write_static_availability_calendar(
    annual_load: list[dict[str, str]], target_data: Path
) -> None:
    rows = [{column: row[column] for column in TIME_COLUMNS} for row in annual_load]
    write_csv(
        target_data / "gen_availability_timeseries.csv",
        TIME_COLUMNS,
        rows,
    )


def nodal_interchange_weights(source_pcm_data: Path, bus_ids: list[str]) -> dict[str, float]:
    _, cap_rows = read_csv(source_pcm_data / "ni_timeseries_nodal_cap.csv")
    if not cap_rows:
        raise ValueError("Source nodal interchange-cap file is empty")
    first = cap_rows[0]
    missing = [bus for bus in bus_ids if bus not in first]
    if missing:
        raise ValueError(f"Interchange-cap file is missing {len(missing)} bus columns")
    values = {bus: float(first[bus]) for bus in bus_ids}
    total = sum(values.values())
    if total <= 0:
        raise ValueError("Source nodal interchange-cap row has no positive capacity")
    weights = {bus: value / total for bus, value in values.items()}
    if abs(sum(weights.values()) - 1.0) > 1.0e-10:
        raise ValueError("Nodal interchange weights do not sum to one")
    return weights


def write_annual_nodal_files(
    annual_load: list[dict[str, str]],
    source_pcm_data: Path,
    target_pcm_data: Path,
) -> dict[str, float]:
    _, buses = read_csv(target_pcm_data / "busdata.csv")
    _, zones = read_csv(target_pcm_data / "zonedata.csv")
    _, branches = read_csv(target_pcm_data / "branchdata.csv")
    if len(buses) != EXPECTED_BUSES:
        raise ValueError(f"Expected {EXPECTED_BUSES} buses, found {len(buses)}")
    if len(branches) != EXPECTED_BRANCHES:
        raise ValueError(f"Expected {EXPECTED_BRANCHES} branches, found {len(branches)}")

    bus_ids = [row["Bus_id"] for row in buses]
    if len(set(bus_ids)) != len(bus_ids):
        raise ValueError("busdata.csv contains duplicate Bus_id values")
    bus_zone = {row["Bus_id"]: row["Zone_id"] for row in buses}
    unknown_zones = sorted(set(bus_zone.values()) - set(INTERNAL_ZONES) - {"EXT"})
    if unknown_zones:
        raise ValueError(f"Unsupported bus zones: {unknown_zones}")

    zone_peak = {row["Zone_id"]: float(row["Demand (MW)"]) for row in zones}
    missing_peaks = sorted(set(INTERNAL_ZONES) - set(zone_peak))
    if missing_peaks:
        raise ValueError(f"zonedata.csv is missing demand for {missing_peaks}")

    weights = nodal_interchange_weights(source_pcm_data, bus_ids)
    nodal_path = target_pcm_data / "load_timeseries_nodal.csv"
    target_path = target_pcm_data / "ni_timeseries_nodal_target.csv"
    cap_path = target_pcm_data / "ni_timeseries_nodal_cap.csv"
    fieldnames = [*TIME_COLUMNS, *bus_ids]

    with (
        nodal_path.open("w", newline="", encoding="utf-8") as nodal_handle,
        target_path.open("w", newline="", encoding="utf-8") as target_handle,
        cap_path.open("w", newline="", encoding="utf-8") as cap_handle,
    ):
        nodal_writer = csv.DictWriter(
            nodal_handle, fieldnames=fieldnames, lineterminator="\n"
        )
        target_writer = csv.DictWriter(
            target_handle, fieldnames=fieldnames, lineterminator="\n"
        )
        cap_writer = csv.DictWriter(
            cap_handle, fieldnames=fieldnames, lineterminator="\n"
        )
        nodal_writer.writeheader()
        target_writer.writeheader()
        cap_writer.writeheader()

        annual_peak_energy = 0.0
        annual_cap_energy = 0.0
        for row in annual_load:
            time = {column: row[column] for column in TIME_COLUMNS}
            nodal = dict(time)
            target = dict(time)
            cap = dict(time)
            hourly_load = sum(float(row[zone]) * zone_peak[zone] for zone in INTERNAL_ZONES)
            annual_peak_energy += hourly_load
            for bus_id in bus_ids:
                zone = bus_zone[bus_id]
                nodal[bus_id] = row[zone] if zone in INTERNAL_ZONES else "0.0"
                target[bus_id] = "0.0"
                cap_value = hourly_load * weights[bus_id]
                cap[bus_id] = format(cap_value, ".12g")
                annual_cap_energy += cap_value
            nodal_writer.writerow(nodal)
            target_writer.writerow(target)
            cap_writer.writerow(cap)

    if abs(annual_peak_energy - annual_cap_energy) > max(1.0e-4, annual_peak_energy * 1.0e-10):
        raise ValueError(
            "Annual nodal interchange caps do not reconcile with hourly system load"
        )
    return {
        "annual_system_load_proxy_mwh": annual_peak_energy,
        "annual_nodal_interchange_cap_sum_mwh": annual_cap_energy,
        "interchange_weight_sum": sum(weights.values()),
    }


def build_case_skeletons() -> tuple[Path, Path]:
    if TARGET_GTEP.exists() or TARGET_PCM.exists():
        raise FileExistsError(
            "One or both target cases already exist. The builder never overwrites cases."
        )
    TARGET_GTEP.mkdir()
    TARGET_PCM.mkdir()

    source_gtep_data = SOURCE_GTEP / "Data_MD_GTEP_RPS20_4zone_public"
    source_pcm_data = SOURCE_PCM / "Data_MD_PCM_RPS20_transmission_public"
    target_gtep_data = TARGET_GTEP / GTEP_DATA_NAME
    target_pcm_data = TARGET_PCM / PCM_DATA_NAME
    copy_tree(source_gtep_data, target_gtep_data)
    copy_tree(source_pcm_data, target_pcm_data)
    copy_tree(SOURCE_GTEP / "references", TARGET_GTEP / "references")
    # Retain source-data provenance, maps, and physical-network references, but
    # never carry solved-output snapshots from the shorter source benchmark into
    # a newly generated annual case. Those results describe a different solve.
    shutil.copytree(
        SOURCE_PCM / "references",
        TARGET_PCM / "references",
        ignore=shutil.ignore_patterns("validation", "GUROBI_VALIDATION.md"),
    )
    copy_tree(SOURCE_GTEP / "Settings", TARGET_GTEP / "Settings")
    copy_tree(SOURCE_PCM / "Settings", TARGET_PCM / "Settings")
    if (SOURCE_PCM / "LICENSE_DATA.md").is_file():
        shutil.copy2(SOURCE_PCM / "LICENSE_DATA.md", TARGET_PCM / "LICENSE_DATA.md")

    rep_weights = target_gtep_data / "rep_period_weights.csv"
    if rep_weights.exists():
        rep_weights.unlink()
    return target_gtep_data, target_pcm_data


def write_operational_template_registry(
    target_gtep_data: Path, target_pcm_data: Path
) -> None:
    """Write PCM-owned operating assumptions referenced by GTEP candidates."""
    candidate_path = target_gtep_data / "gendata_candidate.csv"
    candidate_header, candidate_rows = read_csv(candidate_path)
    required_candidate_columns = {
        "Operational_Template_ID",
        "Flag_UC",
        "Min_down_time",
        "Min_up_time",
        "Start_up_cost ($/MW)",
    }
    missing = required_candidate_columns.difference(candidate_header)
    if missing:
        raise ValueError(
            f"Generation candidates are missing operational columns: {sorted(missing)}"
        )
    # These columns do not affect the GTEP formulation. Blank placeholders make
    # template ownership explicit while preserving candidate > template precedence
    # whenever a user supplies a case-specific value.
    for row in candidate_rows:
        for column in (
            "Flag_UC",
            "Min_down_time",
            "Min_up_time",
            "Start_up_cost ($/MW)",
        ):
            row[column] = ""
    write_csv(candidate_path, candidate_header, candidate_rows)

    template_header = [
        "Operational_Template_ID",
        "Resource_Kind",
        "Type",
        "Flag_thermal",
        "Flag_VRE",
        "Flag_mustrun",
        "Flag_UC",
        "Min_down_time",
        "Min_up_time",
        "Start_up_cost ($/MW)",
        "FOR",
        "RM_SPIN",
        "RU",
        "RD",
        "Charging efficiency",
        "Discharging efficiency",
        "Charging Rate",
        "Discharging Rate",
        "Source",
        "Notes",
    ]
    blank = {column: "" for column in template_header}
    templates = [
        {
            **blank,
            "Operational_Template_ID": "HOPE_NGCC_DEFAULT",
            "Resource_Kind": "generation",
            "Type": "NGCC",
            "Flag_thermal": "1",
            "Flag_VRE": "0",
            "Flag_mustrun": "0",
            "Flag_UC": "1",
            "Min_down_time": "2",
            "Min_up_time": "2",
            "Start_up_cost ($/MW)": "15.0",
            "FOR": "0.04",
            "RM_SPIN": "0.1",
            "RU": "0.6",
            "RD": "0.6",
            "Source": "HOPE Maryland benchmark assumption",
            "Notes": (
                "Modern flexible combined-cycle unit; candidate-specific values "
                "retain precedence"
            ),
        },
        {
            **blank,
            "Operational_Template_ID": "HOPE_SolarPV_DEFAULT",
            "Resource_Kind": "generation",
            "Type": "SolarPV",
            "Flag_thermal": "0",
            "Flag_VRE": "1",
            "Flag_mustrun": "0",
            "Flag_UC": "0",
            "Min_down_time": "0",
            "Min_up_time": "0",
            "Start_up_cost ($/MW)": "0.0",
            "FOR": "0.0",
            "RM_SPIN": "0.0",
            "RU": "1.0",
            "RD": "1.0",
            "Source": "HOPE Maryland benchmark assumption",
            "Notes": "Non-committed variable renewable resource",
        },
        {
            **blank,
            "Operational_Template_ID": "HOPE_WindOn_DEFAULT",
            "Resource_Kind": "generation",
            "Type": "WindOn",
            "Flag_thermal": "0",
            "Flag_VRE": "1",
            "Flag_mustrun": "0",
            "Flag_UC": "0",
            "Min_down_time": "0",
            "Min_up_time": "0",
            "Start_up_cost ($/MW)": "0.0",
            "FOR": "0.0",
            "RM_SPIN": "0.0",
            "RU": "1.0",
            "RD": "1.0",
            "Source": "HOPE Maryland benchmark assumption",
            "Notes": "Non-committed variable renewable resource",
        },
        {
            **blank,
            "Operational_Template_ID": "HOPE_BATTERY_4H_DEFAULT",
            "Resource_Kind": "storage",
            "Type": "Battery",
            "Charging efficiency": "0.92",
            "Discharging efficiency": "0.92",
            "Charging Rate": "1.0",
            "Discharging Rate": "1.0",
            "Source": "HOPE Maryland benchmark assumption",
            "Notes": "Four-hour battery operating template",
        },
    ]
    write_csv(
        target_pcm_data / "operational_resource_templates.csv",
        template_header,
        templates,
    )


def write_settings_and_metadata(
    target_gtep_data: Path,
    target_pcm_data: Path,
    validation_metrics: dict[str, float],
) -> None:
    write_operational_template_registry(target_gtep_data, target_pcm_data)
    write_text(
        TARGET_PCM / "Settings" / "HOPE_holistic_acceptance.yml",
        """
schema_version: 1
require_all: true
required_settings:
  gtep:
    clean_energy_policy: 2
    planning_reserve_mode: 1
    operation_reserve_mode: 1
    holistic_spatial_basis: zone
  pcm:
    clean_energy_policy: 2
    unit_commitment: 1
    operation_reserve_mode: 2
    network_model: 2
thresholds:
  operational_template_assets:
    minimum: 1
  new_thermal_generation_all_uc:
    minimum: 1
  new_generation_mw:
    minimum: 0.001
  pcm_new_generation_dispatch_mwh:
    minimum: 0.001
  gtep_operating_reserve_mwh:
    minimum: 0.001
  pcm_operating_reserve_mwh:
    minimum: 0.001
  gtep_rps_slack_mwh:
    maximum: 0.000001
  pcm_rps_slack_mwh:
    maximum: 0.000001
  pcm_load_shedding_mwh:
    maximum: 0.000001
""",
    )
    # GTEP currently represents operating reserve with one upward SPIN proxy.
    # Match that proxy to PCM's 1% REG-UP + 3% SPIN + 3% NSPIN requirement so
    # aggregate planning does not underbuild capability needed in operations.
    singlepar_path = target_gtep_data / "single_parameter.csv"
    singlepar_header, singlepar_rows = read_csv(singlepar_path)
    if len(singlepar_rows) != 1 or "spin_requirement" not in singlepar_header:
        raise ValueError(f"Unexpected GTEP single-parameter schema: {singlepar_path}")
    singlepar_rows[0]["spin_requirement"] = "0.07"
    write_csv(singlepar_path, singlepar_header, singlepar_rows)

    # The four-zone planning model cannot see this intra-PEPCO constraint. A
    # detailed July screen found the inferred 500 MW rating binding in the only
    # load-shedding hour, so retain a transparent 600 MW calibration assumption.
    branch_path = target_pcm_data / "branchdata.csv"
    branch_header, branch_rows = read_csv(branch_path)
    matches = [
        row for row in branch_rows if row["Corridor_ID"] == DELIVERABILITY_CORRIDOR
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one branch for {DELIVERABILITY_CORRIDOR}; found {len(matches)}"
        )
    branch = matches[0]
    if float(branch["Forward Capacity (MW)"]) != DELIVERABILITY_ORIGINAL_MW or float(
        branch["Reverse Capacity (MW)"]
    ) != DELIVERABILITY_ORIGINAL_MW:
        raise ValueError(f"Unexpected source rating for {DELIVERABILITY_CORRIDOR}")
    branch["Forward Capacity (MW)"] = str(DELIVERABILITY_ADJUSTED_MW)
    branch["Reverse Capacity (MW)"] = str(DELIVERABILITY_ADJUSTED_MW)
    write_csv(branch_path, branch_header, branch_rows)

    write_csv(
        TARGET_PCM / "references" / "physical_deliverability_adjustments.csv",
        [
            "Corridor_ID",
            "from_bus",
            "to_bus",
            "original_forward_mw",
            "original_reverse_mw",
            "adjusted_forward_mw",
            "adjusted_reverse_mw",
            "screening_case",
            "reason",
            "status",
        ],
        [
            {
                "Corridor_ID": DELIVERABILITY_CORRIDOR,
                "from_bus": branch["from_bus"],
                "to_bus": branch["to_bus"],
                "original_forward_mw": DELIVERABILITY_ORIGINAL_MW,
                "original_reverse_mw": DELIVERABILITY_ORIGINAL_MW,
                "adjusted_forward_mw": DELIVERABILITY_ADJUSTED_MW,
                "adjusted_reverse_mw": DELIVERABILITY_ADJUSTED_MW,
                "screening_case": "annual GTEP plus July 744-hour PCM",
                "reason": (
                    "Four-zone GTEP cannot represent this intra-PEPCO constraint; "
                    "the original inferred 500 MW rating bound during the sole "
                    "29.84 MWh shedding hour"
                ),
                "status": "modeled_assumption",
            }
        ],
    )
    source_register_path = TARGET_PCM / "references" / "source_data_register.csv"
    source_header, source_rows = read_csv(source_register_path)
    source_rows.append(
        {
            "Dataset": "HOPE full-year deliverability screen",
            "Role": "Intra-zonal branch calibration",
            "Source": "HOPE annual GTEP to July PCM validation",
            "License_or_terms": "Modeled assumption",
            "Transformation": (
                "Increase inferred rating of OSM_L1528639488 from 500 to 600 MW "
                "in both directions after the four-zone plan produced 29.84 MWh "
                "of shedding in one PEPCO hour at the binding branch"
            ),
        }
    )
    source_rows.append(
        {
            "Dataset": "HOPE operational templates",
            "Role": "New-resource operating assumptions",
            "Source": "HOPE model-development assumptions",
            "License_or_terms": "Modeled assumption",
            "Transformation": (
                "Define modern NGCC commitment and startup behavior plus solar, "
                "wind, and four-hour battery defaults; candidate-specific values "
                "retain precedence"
            ),
        }
    )
    write_csv(source_register_path, source_header, source_rows)

    write_text(
        TARGET_GTEP / ".gitignore",
        """
output/
output_*/
*.log
""",
    )
    write_text(
        TARGET_PCM / ".gitignore",
        """
output/
output_*/
output_holistic/
*.log
""",
    )
    write_text(
        TARGET_GTEP / "Settings" / "HOPE_model_settings.yml",
        f"""
DataCase: {GTEP_DATA_NAME}/              # Four-zone planning view with 8760 chronological hours
model_mode: GTEP
holistic_spatial_basis: zone             # Realize zonal decisions at predefined physical buses
resource_aggregation: 0                  # Preserve stable Asset_ID rows for transfer
endogenous_rep_day: 0
external_rep_day: 0                      # Full chronological year; Time Period remains 1
flexible_demand: 0                       # No validated public-data DR inputs
inv_dcs_bin: 0                           # Continuous builds keep the annual benchmark tractable
carbon_policy: 0                         # Isolate RPS and physical realization
clean_energy_policy: 2                   # Local Maryland 20% RPS
planning_reserve_mode: 1                 # System-level 15% planning reserve
operation_reserve_mode: 1                # GTEP spinning reserve
transmission_expansion: 1
transmission_loss: 0                     # OSM does not provide validated resistance data
storage_ld_duration_hours: 12
write_shadow_prices: 0
summary_table: 1
save_postprocess_snapshot: 0
solver: gurobi                          # Canonical annual validation solver
debug: 0
""",
    )
    write_text(
        TARGET_PCM / "Settings" / "HOPE_model_settings.yml",
        f"""
DataCase: {PCM_DATA_NAME}/               # Self-contained 656-bus, 8760-hour Maryland input
model_mode: PCM
holistic_spatial_basis: auto
resource_aggregation: 0                  # Preserve generator-level Asset_ID values
endogenous_rep_day: 0
external_rep_day: 0                      # Full chronological year; Time Period remains 1
flexible_demand: 0                       # No validated public-data DR inputs
clean_energy_policy: 2                   # Same local Maryland 20% RPS as GTEP
carbon_policy: 0
operation_reserve_mode: 2                # REG-UP/DOWN, SPIN, and NSPIN
network_model: 2                         # 656-bus nodal angle-based DCOPF
transmission_loss: 0                     # OSM does not provide validated resistance data
reference_bus: 1
inv_dcs_bin: 0
time_periods:
    1 : (3, 20, 6, 20)
    2 : (6, 21, 9, 21)
    3 : (9, 22, 12, 20)
    4 : (12, 21, 3, 19)
unit_commitment: 1
write_shadow_prices: 0
summary_table: 1
solver: gurobi                          # Canonical annual validation solver
debug: 0
""",
    )

    write_text(TARGET_GTEP / "run_case.jl", "using HOPE\nHOPE.run_hope(@__DIR__)")
    write_text(TARGET_PCM / "run_case.jl", "using HOPE\nHOPE.run_hope(@__DIR__)")
    write_text(
        TARGET_GTEP / "run_holistic_pair.jl",
        f"""
using HOPE

const GTEP_CASE = @__DIR__
const PCM_CASE = normpath(joinpath(@__DIR__, "..", "{TARGET_PCM.name}"))

result = HOPE.run_hope_holistic(GTEP_CASE, PCM_CASE)
report = HOPE.write_holistic_coverage_report(
    result,
    joinpath(PCM_CASE, "Settings", "HOPE_holistic_acceptance.yml");
    require_all = true,
)
println("Holistic coverage passed: ", report["all_passed"])
""",
    )

    write_text(
        TARGET_GTEP / "manifest.yml",
        f"""
schema_version: 1
case_name: {TARGET_GTEP.name}
model_mode: GTEP
data_subdir: {GTEP_DATA_NAME}/
source_case: ../{SOURCE_GTEP.name}
chronology_source: ../MD_GTEP_holistic_full8760_case_v20260406g/Data_100RPS/
paired_pcm_case: ../{TARGET_PCM.name}
scenario:
  name: Maryland 20% local RPS full-year OSM holistic benchmark
  rps_fraction: 0.20
  rps_scope: Maryland
  clean_energy_policy_mode: 2
spatial_basis: zone
physical_realization_contract: Settings/HOPE_physical_realization.yml
chronology:
  hours: 8760
  mode: full_chronology
  time_period_value: 1
resolution:
  maryland_planning_zones: 4
  external_boundary_zones: 1
  pcm_physical_buses: 656
  pcm_physical_branches: 838
availability:
  method: static generator AF and FOR parameters
  reason: no identity-compatible annual unit-outage trace is available
validation:
  structural_status: passed
  full_year_gtep_status: optimal
  full_year_pcm_status: memory_limited_during_model_construction
  bounded_pcm_status: july_744h_optimal_all_acceptance_checks_passed
  record: ../{TARGET_PCM.name}/references/VALIDATION.md
""",
    )
    write_text(
        TARGET_PCM / "manifest.yml",
        f"""
schema_version: 1
case_name: {TARGET_PCM.name}
model_mode: PCM
data_subdir: {PCM_DATA_NAME}/
source_case: ../{SOURCE_PCM.name}
chronology_source: ../MD_GTEP_holistic_full8760_case_v20260406g/Data_100RPS/
paired_gtep_case: ../{TARGET_GTEP.name}
scenario:
  name: Maryland 20% local RPS full-year OSM holistic benchmark
  rps_fraction: 0.20
  rps_scope: Maryland
  clean_energy_policy_mode: 2
chronology:
  start: January 1 hour 1
  end: December 31 hour 24
  hours: 8760
  mode: full_chronology
geography:
  internal_region: Maryland
  planning_zones: [APS_MD, BGE, DPL_MD, PEPCO]
  external_boundary_zone: EXT
network:
  source: OpenStreetMap contributors via Overpass API
  source_license: ODbL-1.0
  buses: 656
  branches: 838
  formulation: nodal DCOPF angle
  parameters: inferred and explicitly flagged
  deliverability_adjustment: OSM_L1528639488 increased from 500 to 600 MW
operations:
  unit_commitment: true
  operational_template_registry: {PCM_DATA_NAME}/operational_resource_templates.csv
  new_thermal_commitment_policy: Flag_UC = 1
  reserve_mode: REG-UP, REG-DOWN, SPIN, NSPIN
  interchange_target: 0 MW
  interchange_capacity: endogenous hourly boundary cap
availability:
  method: static generator AF and FOR parameters
  reason: no identity-compatible annual unit-outage trace is available
reserve_alignment:
  pcm_upward_requirement_fraction: 0.07
  gtep_spin_proxy_fraction: 0.07
  rationale: GTEP's single upward-reserve product proxies PCM REG-UP plus SPIN plus NSPIN
validation:
  structural_status: passed
  full_year_gtep_status: optimal
  full_year_pcm_status: memory_limited_during_model_construction
  bounded_pcm_status: july_744h_optimal_all_acceptance_checks_passed
  record: references/VALIDATION.md
  summary_metrics: references/july_linkage_validation_summary.csv
""",
    )

    readme = f"""
# Maryland 20% RPS full-year OSM GTEP benchmark

This is the planning stage of HOPE's canonical Maryland annual GTEP-to-PCM
benchmark. It retains four Maryland planning zones plus an explicit external
boundary, uses all 8760 chronological hours, and realizes its investments in
the paired 656-bus PCM case `{TARGET_PCM.name}`.

The spatial inputs, stable asset identities, candidate bus assignments, OSM
network provenance, and version-1 physical-realization contract come from the
validated 168-hour public-data benchmark. Annual normalized load, wind, and
solar profiles come from the retained Maryland full-year chronology. The RPS
target is 20% for Maryland and zero for the external boundary.

GTEP's single upward-reserve product is set to 7% of hourly load. This is the
sum of PCM's 1% REG-UP, 3% SPIN, and 3% NSPIN requirements, preventing the
planning stage from understating the upward operating capability required by
the detailed operational stage.

Each candidate references a PCM-owned `Operational_Template_ID`. The paired PCM
case defines modern NGCC, solar, wind, and four-hour battery operating
assumptions in `operational_resource_templates.csv`. Candidate-specific values
take precedence, but new thermal resources are always realized with
`Flag_UC = 1`.

`Time Period` is 1 for every row because this is full chronological mode, not
representative-day mode. No identity-compatible annual generator-outage trace
is available, so the generator availability CSV contains only aligned calendar
columns and HOPE uses each generator's `AF` and `FOR` parameters. The July
outage pattern from the 168-hour case is not repeated throughout the year.

Run the linked pair with:

```powershell
julia --project=. ModelCases/{TARGET_GTEP.name}/run_holistic_pair.jl
```

This public-data system is a geographically grounded synthetic benchmark, not
an official PJM network model. Electrical parameters, external-boundary limits,
and candidate siting remain documented modeling assumptions.

## Validation status

The full 8760-hour GTEP stage solved to `OPTIMAL` with Gurobi, zero load
shedding, and zero RPS slack. The physical handoff and detailed PCM formulation
were then validated on all 744 hours of July; PCM also solved to `OPTIMAL` and
passed every acceptance check with zero load shedding and zero RPS slack.

The 656-bus, 8760-hour PCM case is intentionally retained at full resolution.
Its monolithic construction exceeded memory on the 32 GB validation workstation
(about 27.6 GB private memory at failure). This is a compute-resource limit, not
a successful annual PCM solve. See the paired PCM case's
`references/VALIDATION.md` for the exact scope and reproduction commands.
"""
    write_text(TARGET_GTEP / "README.md", readme)

    write_text(
        TARGET_PCM / "README.md",
        f"""
# Maryland 20% RPS full-year OSM PCM benchmark

This is the 8760-hour operational stage paired with `{TARGET_GTEP.name}`. It
retains 656 buses and 838 branches from the documented OSM-derived Maryland
transmission reconstruction and uses nodal angle-based DCOPF, unit commitment,
four operating-reserve products, storage chronology, and a local 20% Maryland
RPS.

The annual nodal load multipliers are derived deterministically from the annual
four-zone profiles and each bus's `Zone_id`. Maryland is not electrically
isolated: `EXT` boundary buses and branches remain in the network. Net
interchange has a zero schedule because no authoritative hourly schedule is
assumed, while hourly nodal interchange caps allow endogenous imports and
exports within the documented boundary-interface limits.

Generator-specific annual outage traces are not available with compatible
stable identities. The case therefore uses generator-level `AF` and `FOR`
parameters rather than repeating one July week across the year.

The data folder contains `operational_resource_templates.csv`, the PCM-owned
registry for new GTEP-built generators and storage. Explicit candidate values
take precedence; missing operating values come from the referenced template and
then the legacy PCM fleet-average/default fallback. New thermal generation is
always unit committed. Existing PCM resource rows are not overwritten.

The exact post-GTEP physical tables used by PCM are written under
`output_holistic/realized_inputs/`; source `Data/` files remain unchanged.
The same folder includes `operational_parameters_audit.csv`, which identifies
candidate, template, and thermal-policy parameter sources.
This is a research workflow benchmark, not an official PJM planning case.

The four-zone planning model cannot represent every intra-zonal constraint. A
July deliverability screen found one PEPCO 69 kV branch at its inferred 500 MW
limit during the only load-shedding hour. The benchmark therefore calibrates
`OSM_L1528639488` to 600 MW in both directions. This is explicitly recorded as
a modeled assumption in `references/physical_deliverability_adjustments.csv`.

## Validation status

The source case remains a complete 8760-hour input. Full-year GTEP solved to
`OPTIMAL`; the strict GTEP-to-PCM handoff and the detailed PCM constraints were
validated on a 744-hour July slice, which solved to `OPTIMAL` with zero load
shedding, zero RPS slack, and every configured acceptance check passing.

The monolithic 8760-hour PCM construction exceeded the 32 GB workstation's
memory (about 27.6 GB private memory at failure). No hours or network elements
were removed from this published case to conceal that limit. See
`references/VALIDATION.md` for commands, metrics, and interpretation.

The validation folder also contains
`references/july_linkage_validation_summary.csv`, a compact machine-readable
summary derived from the solved annual GTEP and July PCM outputs.
""",
    )

    write_text(
        TARGET_PCM / "references" / "VALIDATION.md",
        f"""
# Validation record

Validated on 2026-10-20 (America/New_York) with Gurobi 13.0.0.

## What passed

- The 8760-hour, four-zone GTEP stage reached `OPTIMAL` with objective
  2,396,599,492.17 USD, zero load shedding, and zero RPS slack.
- The strict physical-realization audit passed for 271 existing generators,
  12 generation candidates, 4 storage candidates, 838 branches, and 656 buses.
- The PCM-owned operational-template registry populated all three built NGCC
  rows with `Flag_UC = 1`, two-hour minimum up/down times, and a 15 USD/MW
  startup-cost assumption. The field-level provenance audit passed.
- The detailed network has one connected component containing every planning
  zone and the external boundary.
- A bounded end-to-end validation retained the annual GTEP solve and ran the
  complete 656-bus PCM formulation for all 744 hours of July. PCM reached
  `OPTIMAL` with objective 201,932,586.63 USD, zero load shedding, zero RPS
  slack, and all acceptance checks passing.

The July run exercises nodal angle-based DCOPF, unit commitment, REG-UP,
REG-DOWN, SPIN, NSPIN, storage chronology, the local 20% RPS, transferred new
generation and storage, operational-template realization, source-case
immutability, and strict physical mapping.
It is a functional integration validation, not an annual operating result.

## Demonstrated workflow

1. GTEP reads 8760 chronological hours at four Maryland planning zones plus
   `EXT` and selects annual investments.
2. The physical-realization contract maps every selected candidate to a
   predefined PCM bus. HOPE writes realized generator, storage, and branch
   tables under `output_holistic/realized_inputs/` without changing either
   source case.
3. PCM reads July's 744 chronological hours on 656 buses and 838 branches and
   operates the transferred system with unit commitment, DC power flow,
   reserves, storage chronology, and the local RPS.
4. Machine-readable reconciliation and acceptance tables compare the planning
   outputs, realized PCM inputs, and operating results.

### Annual GTEP decisions transferred to PCM

| Zone | New NGCC (MW) | New solar (MW) | Battery power (MW) | Battery energy (MWh) |
| --- | ---: | ---: | ---: | ---: |
| APS_MD | 1,341.6 | 3,557.7 | 1,399.7 | 5,598.9 |
| BGE | 2,666.9 | 3,085.7 | 1,400.0 | 5,599.9 |
| DPL_MD | 0.0 | 1,660.5 | 1,347.7 | 5,390.8 |
| PEPCO | 5,000.0 | 2,586.2 | 668.4 | 2,673.6 |
| **Total** | **9,008.5** | **10,890.1** | **4,815.8** | **19,263.2** |

Seven generation candidates and all four storage candidates were built. No
retirements or candidate transmission additions were selected in this solve.
Those transfer paths remain configured but were not exercised by this result.

### Transfer reconciliation

| Check | GTEP decision | Realized PCM input | Result |
| --- | ---: | ---: | --- |
| New generation | 19,898.519 MW | 19,898.519 MW | Pass |
| New storage power | 4,815.806 MW | 4,815.806 MW | Pass |
| New storage energy | 19,263.225 MWh | 19,263.225 MWh | Pass |
| Existing generator crosswalk | 271 assets | 271 assets | Pass |
| Candidate bus references | 16 candidates | 16 resolved | Pass |
| Source-case integrity | GTEP and PCM | unchanged | Pass |

### July PCM operating evidence

| Metric | Result |
| --- | ---: |
| PCM objective | 201,932,586.63 USD |
| Transferred new-generation dispatch | 5,863,755.3 MWh |
| Transferred storage charge | 356,810.5 MWh |
| Transferred storage discharge | 302,004.4 MWh |
| Operating reserve carried | 1,386,920.8 MWh |
| Maximum absolute branch flow | 4,816.4 MW |
| Load shedding | 0.0 MWh |
| RPS slack | 0.0 MWh |
| Acceptance checks | All passed |

The compact machine-readable record is
`references/july_linkage_validation_summary.csv`. The original run evidence is
under `artifacts/agent_runs/md-rps20-operational-template-july-v2/` in the HOPE
working tree; generated artifacts are intentionally not part of the published
input case.

## Interpretation boundary

This result demonstrates a consistent and reproducible GTEP-to-PCM linkage.
It does not establish annual PCM production cost, winter reliability, seasonal
storage performance, or annual operating-policy compliance. The July PCM run
also enforces the 20% local RPS within July, which is a deliberately restrictive
integration test rather than a substitute for annual REC accounting.

## Full-year PCM resource limit

The monolithic 656-bus by 8760-hour PCM was attempted without reducing the
published inputs. Model construction exhausted memory on a 32 GB Windows
workstation at about 27.6 GB private memory and ended with
`ReadOnlyMemoryError`. Therefore, the annual PCM stage is **not claimed as
solved**. Run it on a higher-memory machine; an exact rolling-horizon workflow
would first need explicit commitment, dispatch, storage-SOC, and annual REC
state carry so that it does not change the mathematics.

## Reproduce

Validate the published inputs:

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_rps20_full8760_holistic_pair.py --validate-only
julia --project=. tools/repo_utils/audit_holistic_case_pair.jl ModelCases/{TARGET_GTEP.name} ModelCases/{TARGET_PCM.name}
julia --project=. tools/repo_utils/audit_pcm_network_components.jl ModelCases/{TARGET_PCM.name}
```

Run the full pair on a high-memory machine:

```powershell
julia --project=. ModelCases/{TARGET_GTEP.name}/run_holistic_pair.jl
```

Create the bounded July validation workspace without modifying either source
case, then run it:

```powershell
python ModelCases/tools/md_transmission_case_related/build_md_rps20_full8760_holistic_pair.py --validation-month 7 --validation-root artifacts/agent_runs/md-rps20-july-validation
julia --project=. artifacts/agent_runs/md-rps20-july-validation/run_pair.jl
```
""",
    )

    write_csv(
        TARGET_PCM / "references" / "july_linkage_validation_summary.csv",
        ["Stage", "Metric", "Value", "Unit", "Evidence"],
        [
            {"Stage": "Metadata", "Metric": "validation_date", "Value": "2026-10-20", "Unit": "America/New_York", "Evidence": "reference validation run"},
            {"Stage": "Metadata", "Metric": "solver", "Value": "Gurobi 13.0.0", "Unit": "version", "Evidence": "reference validation run"},
            {"Stage": "Metadata", "Metric": "reference_run_id", "Value": "md-rps20-operational-template-july-v2", "Unit": "identifier", "Evidence": "artifacts/agent_runs"},
            {"Stage": "GTEP", "Metric": "chronology", "Value": 8760, "Unit": "hours", "Evidence": "annual source case"},
            {"Stage": "GTEP", "Metric": "termination_status", "Value": "OPTIMAL", "Unit": "status", "Evidence": "holistic_coverage.yml"},
            {"Stage": "GTEP", "Metric": "objective", "Value": 2396599492.168707, "Unit": "USD", "Evidence": "holistic_coverage.yml"},
            {"Stage": "GTEP", "Metric": "new_generation", "Value": 19898.518913131313, "Unit": "MW", "Evidence": "capacity.csv"},
            {"Stage": "GTEP", "Metric": "new_storage_power", "Value": 4815.8062091904285, "Unit": "MW", "Evidence": "es_capacity.csv"},
            {"Stage": "GTEP", "Metric": "new_storage_energy", "Value": 19263.224836761714, "Unit": "MWh", "Evidence": "es_capacity.csv"},
            {"Stage": "Handoff", "Metric": "existing_assets_crosswalked", "Value": 271, "Unit": "assets", "Evidence": "handoff_contract_checks.csv"},
            {"Stage": "Handoff", "Metric": "generation_candidates_resolved", "Value": 12, "Unit": "candidates", "Evidence": "handoff_contract_checks.csv"},
            {"Stage": "Handoff", "Metric": "storage_candidates_resolved", "Value": 4, "Unit": "candidates", "Evidence": "handoff_contract_checks.csv"},
            {"Stage": "Handoff", "Metric": "new_generation_reconciled", "Value": 19898.518913131313, "Unit": "MW", "Evidence": "transfer_reconciliation_checks.csv"},
            {"Stage": "Handoff", "Metric": "new_storage_power_reconciled", "Value": 4815.8062091904285, "Unit": "MW", "Evidence": "transfer_reconciliation_checks.csv"},
            {"Stage": "Handoff", "Metric": "source_cases_unchanged", "Value": True, "Unit": "boolean", "Evidence": "handoff_contract_checks.csv"},
            {"Stage": "Handoff", "Metric": "operational_template_assets", "Value": 7, "Unit": "assets", "Evidence": "operational_parameters_audit.csv"},
            {"Stage": "Handoff", "Metric": "new_thermal_generation_uc", "Value": 3, "Unit": "resources", "Evidence": "realized_inputs/gendata.csv"},
            {"Stage": "PCM", "Metric": "chronology", "Value": 744, "Unit": "hours", "Evidence": "July validation slice"},
            {"Stage": "PCM", "Metric": "termination_status", "Value": "OPTIMAL", "Unit": "status", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "objective", "Value": 201932586.6348897, "Unit": "USD", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "new_generation_dispatch", "Value": 5863755.34489549, "Unit": "MWh", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "new_storage_charge", "Value": 356810.53578190197, "Unit": "MWh", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "new_storage_discharge", "Value": 302004.4374858025, "Unit": "MWh", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "operating_reserve", "Value": 1386920.782117107, "Unit": "MWh", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "maximum_absolute_branch_flow", "Value": 4816.371082753038, "Unit": "MW", "Evidence": "holistic_coverage.yml"},
            {"Stage": "PCM", "Metric": "load_shedding", "Value": 0.0, "Unit": "MWh", "Evidence": "holistic_acceptance_checks.csv"},
            {"Stage": "PCM", "Metric": "rps_slack", "Value": 0.0, "Unit": "MWh", "Evidence": "holistic_acceptance_checks.csv"},
            {"Stage": "PCM", "Metric": "acceptance_all_passed", "Value": True, "Unit": "boolean", "Evidence": "holistic_acceptance_checks.csv"},
        ],
    )

    gtep_build_validation_path = TARGET_GTEP / "references" / "build_validation.json"
    gtep_build_validation = json.loads(
        gtep_build_validation_path.read_text(encoding="utf-8")
    )
    gtep_build_validation.update(
        {
            "case": TARGET_GTEP.name,
            "hours": EXPECTED_HOURS,
            "source_gtep_case": SOURCE_GTEP.name,
            "paired_pcm_case": TARGET_PCM.name,
            "chronology_source": str(CHRONOLOGY_DATA.relative_to(MODELCASES)),
            "representative_periods": 0,
            "chronology_mode": "full",
            "gtep_upward_reserve_proxy_fraction": 0.07,
            "reserve_alignment_basis": "PCM REG-UP 1% + SPIN 3% + NSPIN 3%",
        }
    )
    gtep_build_validation_path.write_text(
        json.dumps(gtep_build_validation, indent=2) + "\n", encoding="utf-8"
    )

    pcm_build_validation_path = TARGET_PCM / "references" / "build_validation.json"
    pcm_build_validation = json.loads(
        pcm_build_validation_path.read_text(encoding="utf-8")
    )
    pcm_build_validation.update(
        {
            "case": TARGET_PCM.name,
            "hours": EXPECTED_HOURS,
            "source_pcm_case": SOURCE_PCM.name,
            "paired_gtep_case": TARGET_GTEP.name,
            "chronology_source": str(CHRONOLOGY_DATA.relative_to(MODELCASES)),
            "chronology_mode": "full",
            "generator_availability_method": "static AF and FOR parameters",
            "physical_deliverability_adjustment": {
                "corridor_id": DELIVERABILITY_CORRIDOR,
                "original_capacity_mw": DELIVERABILITY_ORIGINAL_MW,
                "adjusted_capacity_mw": DELIVERABILITY_ADJUSTED_MW,
            },
        }
    )
    pcm_build_validation_path.write_text(
        json.dumps(pcm_build_validation, indent=2) + "\n", encoding="utf-8"
    )

    validation = {
        "schema_version": 1,
        "gtep_case": TARGET_GTEP.name,
        "pcm_case": TARGET_PCM.name,
        "chronology_source": str(CHRONOLOGY_DATA.relative_to(MODELCASES)),
        "spatial_source_gtep": SOURCE_GTEP.name,
        "spatial_source_pcm": SOURCE_PCM.name,
        "hours": EXPECTED_HOURS,
        "time_period_values": [1],
        "planning_nodes": 5,
        "maryland_planning_zones": 4,
        "external_boundary_zones": 1,
        "physical_buses": EXPECTED_BUSES,
        "physical_branches": EXPECTED_BRANCHES,
        "rps_fraction": 0.20,
        "gtep_upward_reserve_proxy_fraction": 0.07,
        "pcm_upward_reserve_requirement_fraction": 0.07,
        "physical_deliverability_adjustment": {
            "corridor_id": DELIVERABILITY_CORRIDOR,
            "original_capacity_mw": DELIVERABILITY_ORIGINAL_MW,
            "adjusted_capacity_mw": DELIVERABILITY_ADJUSTED_MW,
        },
        "generator_availability_method": "static AF and FOR parameters",
        "interchange_target_mw": 0.0,
        **validation_metrics,
        "files": {
            "gtep_load_sha256": sha256(target_gtep_data / "load_timeseries_regional.csv"),
            "pcm_nodal_load_sha256": sha256(target_pcm_data / "load_timeseries_nodal.csv"),
            "pcm_ni_cap_sha256": sha256(target_pcm_data / "ni_timeseries_nodal_cap.csv"),
            "pcm_branchdata_sha256": sha256(target_pcm_data / "branchdata.csv"),
            "pcm_operational_templates_sha256": sha256(
                target_pcm_data / "operational_resource_templates.csv"
            ),
        },
        "validation_status": {
            "structural": "passed",
            "full_year_gtep": "optimal",
            "full_year_pcm": "memory_limited_during_model_construction",
            "july_744h_pcm": "optimal_all_acceptance_checks_passed",
        },
    }
    (TARGET_PCM / "references" / "full8760_build_validation.json").write_text(
        json.dumps(validation, indent=2) + "\n", encoding="utf-8"
    )


def validate_generated_pair(target_gtep_data: Path, target_pcm_data: Path) -> None:
    required_time_files = [
        target_gtep_data / "load_timeseries_regional.csv",
        target_gtep_data / "wind_timeseries_regional.csv",
        target_gtep_data / "solar_timeseries_regional.csv",
        target_gtep_data / "gen_availability_timeseries.csv",
        target_pcm_data / "load_timeseries_regional.csv",
        target_pcm_data / "load_timeseries_nodal.csv",
        target_pcm_data / "wind_timeseries_regional.csv",
        target_pcm_data / "solar_timeseries_regional.csv",
        target_pcm_data / "gen_availability_timeseries.csv",
        target_pcm_data / "ni_timeseries_nodal_target.csv",
        target_pcm_data / "ni_timeseries_nodal_cap.csv",
    ]
    for path in required_time_files:
        header, rows = read_csv(path)
        if len(rows) != EXPECTED_HOURS:
            raise ValueError(f"{path} has {len(rows)} rows; expected {EXPECTED_HOURS}")
        missing_time = [column for column in TIME_COLUMNS if column not in header]
        if missing_time:
            raise ValueError(f"{path} is missing time columns {missing_time}")
        if set(row["Time Period"] for row in rows) != {"1"}:
            raise ValueError(f"{path} must use Time Period=1 in full chronology mode")
        if rows[0]["Month"] != "1" or rows[0]["Day"] != "1" or rows[0]["Hours"] != "1":
            raise ValueError(f"{path} has an invalid first hour")
        if rows[-1]["Month"] != "12" or rows[-1]["Day"] != "31" or rows[-1]["Hours"] != "24":
            raise ValueError(f"{path} has an invalid last hour")

    _, target_rows = read_csv(target_pcm_data / "ni_timeseries_nodal_target.csv")
    if any(
        abs(float(value)) > 0.0
        for row in target_rows
        for key, value in row.items()
        if key not in TIME_COLUMNS
    ):
        raise ValueError("Annual nodal interchange target must remain zero")

    _, buses = read_csv(target_pcm_data / "busdata.csv")
    _, branches = read_csv(target_pcm_data / "branchdata.csv")
    _, zones = read_csv(target_pcm_data / "zonedata.csv")
    if len(buses) != EXPECTED_BUSES or len(branches) != EXPECTED_BRANCHES:
        raise ValueError(
            f"Physical network is {len(buses)} buses/{len(branches)} branches; "
            f"expected {EXPECTED_BUSES}/{EXPECTED_BRANCHES}"
        )
    bus_ids = [row["Bus_id"] for row in buses]
    bus_zone = {row["Bus_id"]: row["Zone_id"] for row in buses}
    zone_peak = {row["Zone_id"]: float(row["Demand (MW)"]) for row in zones}
    nodal_header, nodal_rows = read_csv(target_pcm_data / "load_timeseries_nodal.csv")
    cap_header, cap_rows = read_csv(target_pcm_data / "ni_timeseries_nodal_cap.csv")
    regional_header, regional_rows = read_csv(
        target_pcm_data / "load_timeseries_regional.csv"
    )
    expected_nodal_header = [*TIME_COLUMNS, *bus_ids]
    if nodal_header != expected_nodal_header or cap_header != expected_nodal_header:
        raise ValueError("Nodal time-series bus columns do not match busdata order exactly")
    expected_regional = [*TIME_COLUMNS, *INTERNAL_ZONES, "EXT", "NI"]
    if regional_header != expected_regional:
        raise ValueError(
            f"Regional load columns are {regional_header}; expected {expected_regional}"
        )
    for index in (0, EXPECTED_HOURS // 2, EXPECTED_HOURS - 1):
        regional = regional_rows[index]
        nodal = nodal_rows[index]
        cap = cap_rows[index]
        for bus_id in bus_ids:
            zone = bus_zone[bus_id]
            expected = regional[zone] if zone in INTERNAL_ZONES else "0.0"
            if abs(float(nodal[bus_id]) - float(expected)) > 1.0e-12:
                raise ValueError(
                    f"Nodal load mismatch at row {index + 1}, bus {bus_id}"
                )
        hourly_load = sum(
            float(regional[zone]) * zone_peak[zone] for zone in INTERNAL_ZONES
        )
        cap_total = sum(float(cap[bus_id]) for bus_id in bus_ids)
        if abs(hourly_load - cap_total) > max(1.0e-5, hourly_load * 1.0e-10):
            raise ValueError(
                f"Interchange cap mismatch at row {index + 1}: "
                f"expected {hourly_load}, found {cap_total}"
            )

    _, rps_rows = read_csv(target_gtep_data / "rpspolicies.csv")
    md_rps = [
        float(row["RPS"])
        for row in rps_rows
        if row["From_state"] == "MD" and row["To_state"] == "MD"
    ]
    if md_rps != [0.20]:
        raise ValueError(f"Expected one local Maryland 20% RPS row, found {md_rps}")
    _, candidate_rows = read_csv(target_gtep_data / "gendata_candidate.csv")
    template_header, template_rows = read_csv(
        target_pcm_data / "operational_resource_templates.csv"
    )
    required_template_columns = {
        "Operational_Template_ID",
        "Resource_Kind",
        "Type",
        "Flag_UC",
    }
    if not required_template_columns.issubset(template_header):
        raise ValueError("Operational template registry has an invalid schema")
    templates = {row["Operational_Template_ID"]: row for row in template_rows}
    for candidate in candidate_rows:
        template_id = candidate["Operational_Template_ID"]
        if template_id not in templates:
            raise ValueError(f"Missing operational template {template_id}")
        template = templates[template_id]
        if template["Type"] != candidate["Type"]:
            raise ValueError(
                f"Operational template {template_id} type does not match candidate"
            )
        if candidate["Flag_thermal"] == "1" and template["Flag_UC"] != "1":
            raise ValueError(
                f"Thermal candidate {candidate['Candidate_ID']} must use Flag_UC=1"
            )
    _, singlepar_rows = read_csv(target_gtep_data / "single_parameter.csv")
    if len(singlepar_rows) != 1 or float(singlepar_rows[0]["spin_requirement"]) != 0.07:
        raise ValueError("GTEP upward-reserve proxy must equal PCM's 7% total upward requirement")
    calibrated = [
        row
        for row in branches
        if row["Corridor_ID"] == DELIVERABILITY_CORRIDOR
    ]
    if len(calibrated) != 1 or any(
        float(calibrated[0][column]) != DELIVERABILITY_ADJUSTED_MW
        for column in ("Forward Capacity (MW)", "Reverse Capacity (MW)")
    ):
        raise ValueError("Missing or invalid physical deliverability calibration")

    references = target_pcm_data.parent / "references"
    legacy_validation_dir = references / "validation"
    stale = []
    if legacy_validation_dir.is_dir() and any(
        path.is_file() for path in legacy_validation_dir.rglob("*")
    ):
        stale.append(str(legacy_validation_dir))
    legacy_validation_note = references / "GUROBI_VALIDATION.md"
    if legacy_validation_note.exists():
        stale.append(str(legacy_validation_note))
    if stale:
        raise ValueError(
            "Annual case contains validation artifacts copied from a different solve: "
            + ", ".join(stale)
        )
    for required_reference in (
        references / "VALIDATION.md",
        references / "july_linkage_validation_summary.csv",
    ):
        if not required_reference.is_file():
            raise ValueError(f"Missing annual validation reference: {required_reference}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate an existing generated pair without modifying it.",
    )
    parser.add_argument(
        "--validation-month",
        type=int,
        help="Create an isolated annual-GTEP/monthly-PCM integration-test pair.",
    )
    parser.add_argument(
        "--validation-root",
        type=Path,
        help="Destination used with --validation-month.",
    )
    args = parser.parse_args()
    for required in (SOURCE_GTEP, SOURCE_PCM, CHRONOLOGY_DATA):
        if not required.is_dir():
            raise FileNotFoundError(required)

    if args.validate_only:
        target_gtep_data = TARGET_GTEP / GTEP_DATA_NAME
        target_pcm_data = TARGET_PCM / PCM_DATA_NAME
        validate_generated_pair(target_gtep_data, target_pcm_data)
        print(f"Validated {TARGET_GTEP}")
        print(f"Validated {TARGET_PCM}")
        return

    if args.validation_month is not None:
        if args.validation_root is None:
            parser.error("--validation-root is required with --validation-month")
        validate_generated_pair(TARGET_GTEP / GTEP_DATA_NAME, TARGET_PCM / PCM_DATA_NAME)
        materialize_pcm_month_validation(
            args.validation_root.resolve(), args.validation_month
        )
        return
    if args.validation_root is not None:
        parser.error("--validation-root requires --validation-month")

    target_gtep_data, target_pcm_data = build_case_skeletons()
    annual = build_annual_regional_rows()
    write_annual_regional_files(annual, target_gtep_data)
    write_annual_regional_files(annual, target_pcm_data)
    write_static_availability_calendar(
        annual["load_timeseries_regional.csv"], target_gtep_data
    )
    write_static_availability_calendar(
        annual["load_timeseries_regional.csv"], target_pcm_data
    )
    validation_metrics = write_annual_nodal_files(
        annual["load_timeseries_regional.csv"],
        SOURCE_PCM / "Data_MD_PCM_RPS20_transmission_public",
        target_pcm_data,
    )
    write_settings_and_metadata(
        target_gtep_data,
        target_pcm_data,
        validation_metrics,
    )
    validate_generated_pair(target_gtep_data, target_pcm_data)
    print(f"Created {TARGET_GTEP}")
    print(f"Created {TARGET_PCM}")
    print(json.dumps(validation_metrics, indent=2))


if __name__ == "__main__":
    main()
