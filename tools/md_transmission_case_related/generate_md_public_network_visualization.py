"""Generate deterministic geographic reference artifacts for the Maryland case.

The SVG is an offline, code-native view of the reconstructed transmission
topology. Branches are drawn as straight endpoint connections because the
runtime case stores electrical corridors, not full OSM way geometry. The
GeoJSON preserves the same explicit approximation for downstream interactive
viewers.
"""

from __future__ import annotations

import csv
import json
import math
from html import escape
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
MODELCASES = SCRIPT_DIR.parent.parent
PCM_CASE = MODELCASES / "MD_PCM_RPS20_transmission_public_case"
GTEP_CASE = MODELCASES / "MD_GTEP_RPS20_4zone_public_case"
PCM_DATA = PCM_CASE / "Data_MD_PCM_RPS20_transmission_public"
REFERENCES = PCM_CASE / "references"

ZONE_COLORS = {
    "APS_MD": "#e8590c",
    "BGE": "#1971c2",
    "DPL_MD": "#2b8a3e",
    "PEPCO": "#862e9c",
    "EXT": "#868e96",
}

VOLTAGE_COLORS = {
    69: "#adb5bd",
    115: "#74c0fc",
    138: "#4dabf7",
    230: "#4263eb",
    345: "#7048e8",
    500: "#e8590c",
    765: "#c92a2a",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def numeric(value: str | None, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except ValueError:
        return default


def main() -> None:
    buses = read_rows(PCM_DATA / "busdata.csv")
    branches = read_rows(PCM_DATA / "branchdata.csv")
    provenance = {
        row["Branch_ID"]: row for row in read_rows(REFERENCES / "branch_provenance.csv")
    }
    candidate_sites = {
        row["Candidate_Bus"]: row
        for row in read_rows(GTEP_CASE / "references" / "candidate_bus_mapping.csv")
    }
    bus_by_id = {row["Bus_id"]: row for row in buses}

    lats = [numeric(row["Latitude"]) for row in buses]
    lons = [numeric(row["Longitude"]) for row in buses]
    lat_mid = sum(lats) / len(lats)
    lon_scale = math.cos(math.radians(lat_mid))
    scaled_lons = [lon * lon_scale for lon in lons]

    width, height, margin = 1500.0, 1000.0, 75.0
    legend_width = 310.0
    plot_width = width - legend_width - 2 * margin
    plot_height = height - 2 * margin
    min_x, max_x = min(scaled_lons), max(scaled_lons)
    min_y, max_y = min(lats), max(lats)
    scale = min(plot_width / (max_x - min_x), plot_height / (max_y - min_y))
    used_w = (max_x - min_x) * scale
    used_h = (max_y - min_y) * scale
    offset_x = margin + (plot_width - used_w) / 2
    offset_y = margin + (plot_height - used_h) / 2

    def xy(bus: dict[str, str]) -> tuple[float, float]:
        x = offset_x + (numeric(bus["Longitude"]) * lon_scale - min_x) * scale
        y = offset_y + (max_y - numeric(bus["Latitude"])) * scale
        return x, y

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(width)}" height="{int(height)}" viewBox="0 0 {int(width)} {int(height)}">',
        '<rect width="100%" height="100%" fill="#f8f9fa"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif}.small{font-size:13px;fill:#495057}.label{font-size:15px;font-weight:700;fill:#212529}.title{font-size:25px;font-weight:700;fill:#212529}.subtitle{font-size:14px;fill:#495057}</style>',
        '<text x="75" y="38" class="title">Maryland 20% RPS physical-realization reference</text>',
        '<text x="75" y="61" class="subtitle">OSM-derived transmission evidence; straight electrical-corridor endpoints; not an official PJM network map</text>',
        '<text x="75" y="982" class="small">© OpenStreetMap contributors, ODbL 1.0</text>',
    ]

    for branch in branches:
        from_bus = bus_by_id.get(branch["from_bus"])
        to_bus = bus_by_id.get(branch["to_bus"])
        if from_bus is None or to_bus is None:
            continue
        x1, y1 = xy(from_bus)
        x2, y2 = xy(to_bus)
        prov = provenance.get(branch["Corridor_ID"], {})
        voltage = int(round(numeric(prov.get("Voltage_kV"), 0.0)))
        color = VOLTAGE_COLORS.get(voltage, "#ced4da")
        capacity = numeric(branch.get("Forward Capacity (MW)"), 0.0)
        stroke_width = min(3.2, 0.45 + math.log10(max(capacity, 1.0)) / 2.2)
        svg.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{stroke_width:.2f}" stroke-opacity="0.42"/>'
        )

    for bus in buses:
        x, y = xy(bus)
        zone = bus["Zone_id"]
        color = ZONE_COLORS.get(zone, "#868e96")
        if zone == "EXT":
            svg.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="#f8f9fa" stroke="{color}" stroke-width="0.9" opacity="0.8"/>'
            )
        else:
            svg.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.0" fill="{color}" opacity="0.72"/>'
            )

    for bus_id, site in candidate_sites.items():
        bus = bus_by_id[bus_id]
        x, y = xy(bus)
        zone = site["Planning_Zone"]
        svg.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8.0" fill="none" stroke="#ffd43b" stroke-width="3.2"/>'
        )
        svg.append(
            f'<text x="{x + 10:.2f}" y="{y - 8:.2f}" class="label">{escape(zone)}</text>'
        )

    legend_x = width - legend_width + 25
    svg.extend(
        [
            f'<rect x="{legend_x - 18}" y="86" width="{legend_width - 30}" height="835" rx="12" fill="#ffffff" stroke="#dee2e6"/>',
            f'<text x="{legend_x}" y="120" class="label">Planning zones</text>',
        ]
    )
    y = 150
    for zone in ("APS_MD", "BGE", "DPL_MD", "PEPCO", "EXT"):
        svg.append(
            f'<circle cx="{legend_x + 7}" cy="{y - 5}" r="6" fill="{ZONE_COLORS[zone]}"/>'
        )
        svg.append(f'<text x="{legend_x + 24}" y="{y}" class="small">{zone}</text>')
        y += 30

    svg.append(f'<text x="{legend_x}" y="{y + 10}" class="label">Voltage evidence</text>')
    y += 42
    for voltage in sorted(VOLTAGE_COLORS):
        svg.append(
            f'<line x1="{legend_x}" y1="{y - 5}" x2="{legend_x + 26}" y2="{y - 5}" stroke="{VOLTAGE_COLORS[voltage]}" stroke-width="3"/>'
        )
        svg.append(
            f'<text x="{legend_x + 36}" y="{y}" class="small">{voltage} kV</text>'
        )
        y += 28

    svg.extend(
        [
            f'<circle cx="{legend_x + 7}" cy="{y + 12}" r="8" fill="none" stroke="#ffd43b" stroke-width="3"/>',
            f'<text x="{legend_x + 26}" y="{y + 17}" class="small">GTEP realization site</text>',
            f'<text x="{legend_x}" y="{y + 65}" class="label">Case structure</text>',
            f'<text x="{legend_x}" y="{y + 92}" class="small">{len(buses)} buses</text>',
            f'<text x="{legend_x}" y="{y + 116}" class="small">{len(branches)} branches</text>',
            f'<text x="{legend_x}" y="{y + 140}" class="small">4 Maryland zones + EXT</text>',
            f'<text x="{legend_x}" y="{y + 186}" class="small">Line routes are simplified.</text>',
            f'<text x="{legend_x}" y="{y + 208}" class="small">Parameters are inferred and</text>',
            f'<text x="{legend_x}" y="{y + 230}" class="small">documented in provenance CSVs.</text>',
            '</svg>',
        ]
    )
    (REFERENCES / "md_rps20_physical_realization.svg").write_text(
        "\n".join(svg) + "\n", encoding="utf-8"
    )

    features: list[dict] = []
    for bus in buses:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [numeric(bus["Longitude"]), numeric(bus["Latitude"])],
                },
                "properties": {
                    "feature_type": "bus",
                    "bus_id": bus["Bus_id"],
                    "zone": bus["Zone_id"],
                    "state": bus["State"],
                    "candidate_realization_site": bus["Bus_id"] in candidate_sites,
                },
            }
        )
    for branch in branches:
        from_bus = bus_by_id[branch["from_bus"]]
        to_bus = bus_by_id[branch["to_bus"]]
        prov = provenance.get(branch["Corridor_ID"], {})
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [numeric(from_bus["Longitude"]), numeric(from_bus["Latitude"])],
                        [numeric(to_bus["Longitude"]), numeric(to_bus["Latitude"])],
                    ],
                },
                "properties": {
                    "feature_type": "electrical_corridor",
                    "corridor_id": branch["Corridor_ID"],
                    "from_bus": branch["from_bus"],
                    "to_bus": branch["to_bus"],
                    "voltage_kv": numeric(prov.get("Voltage_kV")),
                    "capacity_mw": numeric(branch.get("Forward Capacity (MW)")),
                    "source": prov.get("Source", "inferred"),
                    "geometry_note": "straight endpoint connection; not full OSM way geometry",
                },
            }
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "MD_RPS20_geographically_grounded_synthetic_network",
        "metadata": {
            "authoritative_for_optimization": False,
            "description": "Reference geometry for an OSM-derived synthetic HOPE benchmark, not an official PJM model.",
            "attribution": "OpenStreetMap contributors, ODbL 1.0",
        },
        "features": features,
    }
    (REFERENCES / "md_rps20_network.geojson").write_text(
        json.dumps(geojson, indent=2) + "\n", encoding="utf-8"
    )
    print(REFERENCES / "md_rps20_physical_realization.svg")
    print(REFERENCES / "md_rps20_network.geojson")


if __name__ == "__main__":
    main()
