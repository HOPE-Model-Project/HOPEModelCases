"""Build the Maryland 20% RPS public-data GTEP-to-PCM benchmark pair.

The pair is derived from the versioned Maryland public transmission cases:

* MD_GTEP_4zone_public_case (aggregated planning view)
* MD_PCM_transmission_public_case (656-bus operational view)

The generated cases are self-contained.  The GTEP case uses a moderate local
20% Maryland RPS; the PCM case validates the realized nodal fleet with the same
policy, unit commitment, and operating reserves.  OSM-derived topology remains
an explicitly approximate public-data reconstruction, not an official PJM
network model.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MODELCASES = SCRIPT_DIR.parent.parent

SOURCE_GTEP = MODELCASES / "MD_GTEP_4zone_public_case"
SOURCE_PCM = MODELCASES / "MD_PCM_transmission_public_case"

TARGET_GTEP = MODELCASES / "MD_GTEP_RPS20_4zone_public_case"
TARGET_PCM = MODELCASES / "MD_PCM_RPS20_transmission_public_case"

GTEP_DATA_NAME = "Data_MD_GTEP_RPS20_4zone_public"
PCM_DATA_NAME = "Data_MD_PCM_RPS20_transmission_public"


def copy_tree(source: Path, target: Path, *, ignore=()) -> None:
    if target.exists():
        raise FileExistsError(
            f"Target already exists: {target}. Remove it explicitly before rebuilding."
        )
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*ignore))


def replace_csv_value(path: Path, key_column: str, key: str, value_column: str, value: str) -> None:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"No rows found in {path}")
        fieldnames = list(rows[0])

    matches = 0
    for row in rows:
        if row[key_column] == key:
            row[value_column] = value
            matches += 1
    if matches != 1:
        raise ValueError(f"Expected one {key_column}={key!r} row in {path}, found {matches}")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_local_rps_policy(path: Path) -> None:
    """Write an explicit local Maryland policy with a zero-policy EXT boundary."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("From_state", "To_state", "RPS"))
        writer.writerow(("EXT", "EXT", "0.0"))
        writer.writerow(("MD", "MD", "0.20"))


def replace_single_parameter(path: Path, value_column: str, value: str) -> None:
    """Update one column in HOPE's single-row parameter table."""
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            raise ValueError(f"Expected one parameter row in {path}, found {len(rows)}")
        fieldnames = list(rows[0])
    if value_column not in fieldnames:
        raise KeyError(f"Missing {value_column!r} in {path}")
    rows[0][value_column] = value
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def build_gtep() -> None:
    TARGET_GTEP.mkdir()
    copy_tree(
        SOURCE_GTEP / "Data_MD_GTEP_4zone_public",
        TARGET_GTEP / GTEP_DATA_NAME,
    )
    copy_tree(SOURCE_GTEP / "references", TARGET_GTEP / "references")
    copy_tree(SOURCE_GTEP / "Settings", TARGET_GTEP / "Settings")

    write_local_rps_policy(TARGET_GTEP / GTEP_DATA_NAME / "rpspolicies.csv")

    write(
        TARGET_GTEP / ".gitignore",
        """
output/
output_*/
*.log
""",
    )
    write(
        TARGET_GTEP / "Settings" / "HOPE_model_settings.yml",
        f"""
DataCase: {GTEP_DATA_NAME}/              # Four-zone planning view of the public Maryland network
model_mode: GTEP
holistic_spatial_basis: zone             # Realize zonal decisions at predefined physical buses
resource_aggregation: 0                  # Preserve stable Asset_ID rows for transfer
endogenous_rep_day: 0
external_rep_day: 1                      # Seven July days weighted to a 365-day planning year
flexible_demand: 0                       # No public-data DR assumptions in this benchmark
inv_dcs_bin: 0                           # Continuous builds keep the public benchmark tractable
carbon_policy: 0                         # Isolate the RPS and physical-realization workflow
clean_energy_policy: 2                   # Local annual RPS; no external REC-trading assumption
planning_reserve_mode: 1                 # System-level 15% planning reserve
operation_reserve_mode: 1                # GTEP spinning-reserve constraints
transmission_expansion: 1                # Existing candidate-corridor options remain available
transmission_loss: 0                     # OSM does not provide validated resistance data
storage_ld_duration_hours: 12
write_shadow_prices: 0
summary_table: 1
save_postprocess_snapshot: 0
solver: highs                            # Portable default; validation runner can select Gurobi
debug: 0
""",
    )
    write(
        TARGET_GTEP / "run_case.jl",
        """
using HOPE
HOPE.run_hope(@__DIR__)
""",
    )
    write(
        TARGET_GTEP / "run_holistic_pair.jl",
        """
using HOPE

const GTEP_CASE = @__DIR__
const PCM_CASE = normpath(joinpath(@__DIR__, "..", "MD_PCM_RPS20_transmission_public_case"))

result = HOPE.run_hope_holistic(GTEP_CASE, PCM_CASE)
report = HOPE.write_holistic_coverage_report(
    result,
    joinpath(PCM_CASE, "Settings", "HOPE_holistic_acceptance.yml");
    require_all = true,
)
println("Holistic coverage passed: ", report["all_passed"])
""",
    )
    write(
        TARGET_GTEP / "README.md",
        """
# Maryland 20% RPS four-zone GTEP benchmark

This standalone GTEP case is the aggregated planning stage of the Maryland
20% RPS public-data holistic benchmark. It uses four Maryland utility-planning
zones plus the `EXT` boundary zone, then realizes selected generation, storage,
retirement, and transmission decisions in the paired 656-bus PCM case.

The 20% value is a moderate benchmark policy assumption. It is not inherited
from the legacy `PJM_MD100` name and it is not intended as a policy forecast.
`clean_energy_policy: 2` requires local Maryland renewable generation without
assuming external REC trading. The case also enables system planning reserve,
GTEP spinning reserve, storage investment, and transmission-expansion options.

Every candidate has a predefined physical `Bus_id`; transmission candidates
carry stable `Corridor_ID`, `PCM_from_bus`, and `PCM_to_bus` values. These are
transparent realization assumptions rather than an optimal siting model.

## Run

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_GTEP_RPS20_4zone_public_case/")
```

Run the complete GTEP-to-PCM workflow with:

```powershell
julia --project=. ModelCases/MD_GTEP_RPS20_4zone_public_case/run_holistic_pair.jl
```

The workflow hashes both source cases before and after the run, writes realized
PCM inputs and a handoff manifest under `output_holistic/`, and evaluates the
machine-readable acceptance contract in the paired PCM case.

## Resolution and provenance

The GTEP view is deliberately aggregated to reflect normal planning practice.
The paired PCM case retains the public-data Maryland transmission realization.
Its topology was reconstructed from OpenStreetMap and its electrical parameters
were inferred with documented rules. It is a geographically grounded synthetic
benchmark, not an official PJM power-flow case.
""",
    )

    validation_path = TARGET_GTEP / "references" / "build_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["case"] = TARGET_GTEP.name
    validation["source_gtep_case"] = SOURCE_GTEP.name
    validation["paired_pcm_case"] = TARGET_PCM.name
    validation["rps_fraction"] = 0.20
    validation["rps_mode"] = "local"
    validation_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    write(
        TARGET_GTEP / "manifest.yml",
        f"""
schema_version: 1
case_name: {TARGET_GTEP.name}
model_mode: GTEP
data_subdir: {GTEP_DATA_NAME}/
source_case: ../{SOURCE_GTEP.name}
paired_pcm_case: ../{TARGET_PCM.name}
scenario:
  name: Maryland 20% local RPS holistic benchmark
  rps_fraction: 0.20
  rps_scope: Maryland
  clean_energy_policy_mode: 2
spatial_basis: zone
chronology:
  hours: 168
  external_representative_periods: 7
  total_day_weight: 365
resolution:
  gtep_planning_zones: 5
  pcm_physical_buses: 656
  realization: candidate Bus_id and branch Corridor_ID plus PCM endpoint columns
provenance:
  physical_network: OpenStreetMap-derived public Maryland transmission reconstruction
  electrical_parameters: inferred and documented in the paired PCM case
validation:
  status: pending
""",
    )


def build_pcm() -> None:
    TARGET_PCM.mkdir()
    copy_tree(
        SOURCE_PCM / "Data_MD_PCM_transmission_public",
        TARGET_PCM / PCM_DATA_NAME,
    )
    copy_tree(
        SOURCE_PCM / "references",
        TARGET_PCM / "references",
        ignore=("GUROBI_VALIDATION.md",),
    )
    copy_tree(SOURCE_PCM / "Settings", TARGET_PCM / "Settings")
    shutil.copy2(SOURCE_PCM / "LICENSE_DATA.md", TARGET_PCM / "LICENSE_DATA.md")

    write_local_rps_policy(TARGET_PCM / PCM_DATA_NAME / "rpspolicies.csv")
    for key, value in (
        ("reg_up_requirement", "0.01"),
        ("reg_dn_requirement", "0.01"),
        ("spin_requirement", "0.03"),
        ("nspin_requirement", "0.03"),
    ):
        replace_single_parameter(
            TARGET_PCM / PCM_DATA_NAME / "single_parameter.csv", key, value
        )

    write(
        TARGET_PCM / ".gitignore",
        """
output/
output_*/
output_holistic/
*.log
""",
    )
    write(
        TARGET_PCM / "Settings" / "HOPE_model_settings.yml",
        f"""
DataCase: {PCM_DATA_NAME}/                # Self-contained 656-bus Maryland input folder
model_mode: PCM
holistic_spatial_basis: auto              # Inherit zone realization from the paired GTEP case
resource_aggregation: 0                   # Preserve generator-level Asset_ID values
endogenous_rep_day: 0
flexible_demand: 0                        # No public-data DR assumptions in this benchmark
clean_energy_policy: 2                    # Same local Maryland 20% RPS as GTEP
carbon_policy: 0                          # Isolate RPS and operational realization
operation_reserve_mode: 2                 # REG-UP/DOWN, SPIN, and NSPIN
network_model: 2                          # Nodal angle-based DCOPF
transmission_loss: 0                      # OSM does not provide validated resistance data
reference_bus: 1
inv_dcs_bin: 0
time_periods:
    1 : (3, 20, 6, 20)
    2 : (6, 21, 9, 21)
    3 : (9, 22, 12, 20)
    4 : (12, 21, 3, 19)
unit_commitment: 1                        # Exercise operational commitment after realization
write_shadow_prices: 0                    # MIP prices are not interpreted as LMPs
summary_table: 1
solver: highs                             # Portable default; validation runner can select Gurobi
debug: 0
""",
    )
    write(
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
    write(
        TARGET_PCM / "run_case.jl",
        """
using HOPE
HOPE.run_hope(@__DIR__)
""",
    )
    write(
        TARGET_PCM / "README.md",
        """
# Maryland 20% RPS transmission-level PCM benchmark

This standalone 656-bus PCM case is the operational stage of the Maryland 20%
RPS public-data holistic benchmark. It uses the same OpenStreetMap-derived
transmission realization as `MD_PCM_transmission_public_case` and is paired with
`MD_GTEP_RPS20_4zone_public_case`.

The case enables nodal angle-based DCOPF, unit commitment, generator and storage
chronology, REG-UP, REG-DOWN, SPIN, NSPIN, and a local Maryland 20% RPS. Reserve
requirements are 1% REG-UP, 1% REG-DOWN, 3% SPIN, and 3% NSPIN of system load.
Transmission losses remain disabled because the OSM reconstruction does not
provide validated resistance data.

The topology and ratings are transparent workflow assumptions, not an official
PJM model. See `LICENSE_DATA.md`, `references/source_data_register.csv`, and the
provenance tables for source and inference details.

## Run

```julia
using HOPE
HOPE.run_hope("ModelCases/MD_PCM_RPS20_transmission_public_case/")
```

For the linked run, execute the paired GTEP case's `run_holistic_pair.jl`.
Realized inputs, mapping audits, the handoff manifest, coverage tables, and
acceptance checks are written under this case's `output_holistic/` directory.
""",
    )

    validation_path = TARGET_PCM / "references" / "build_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["case"] = TARGET_PCM.name
    validation["source_pcm_case"] = SOURCE_PCM.name
    validation["paired_gtep_case"] = TARGET_GTEP.name
    validation["rps_fraction"] = 0.20
    validation["reserve_requirements"] = {
        "reg_up": 0.01,
        "reg_down": 0.01,
        "spin": 0.03,
        "nspin": 0.03,
    }
    validation.pop("tested_solution", None)
    validation_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")

    write(
        TARGET_PCM / "manifest.yml",
        f"""
schema_version: 1
case_name: {TARGET_PCM.name}
model_mode: PCM
data_subdir: {PCM_DATA_NAME}/
source_case: ../{SOURCE_PCM.name}
paired_gtep_case: ../{TARGET_GTEP.name}
scenario:
  name: Maryland 20% local RPS holistic benchmark
  rps_fraction: 0.20
  rps_scope: Maryland
  clean_energy_policy_mode: 2
chronology:
  start: July 15 hour 1
  end: July 21 hour 24
  hours: 168
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
operations:
  unit_commitment: true
  reserve_mode: REG-UP, REG-DOWN, SPIN, NSPIN
provenance:
  generator_fleet: PJM DC Health ICARUS21 2025 base input
  load_chronology: legacy PJM_MD100 inputs, used only as chronology provenance
  physical_network: public OSM reconstruction with documented assumptions
validation:
  status: pending
""",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    for required in (SOURCE_GTEP, SOURCE_PCM):
        if not required.is_dir():
            raise FileNotFoundError(required)
    if TARGET_GTEP.exists() or TARGET_PCM.exists():
        raise FileExistsError(
            "One or both target cases already exist. Remove the intended target explicitly "
            "before rebuilding; the builder never overwrites a case."
        )
    build_gtep()
    build_pcm()
    print(f"Created {TARGET_GTEP}")
    print(f"Created {TARGET_PCM}")


if __name__ == "__main__":
    main()
