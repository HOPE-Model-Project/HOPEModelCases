from __future__ import annotations

from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
MODELCASES_ROOT = REPO_ROOT / "ModelCases"
BUS_PATH = MODELCASES_ROOT / "GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8" / "Data_GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8" / "busdata.csv"
LINE_PATH = MODELCASES_ROOT / "GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8" / "Data_GERMANY_PCM_nodal_jan15_2day_resource_cost_case_v8" / "linedata.csv"
ZONE_GEOJSON_PATH = REPO_ROOT / "tools" / "hope_dashboard" / "data" / "germany_tso_zones.geojson"
OUT_MAP = REPO_ROOT / "docs" / "src" / "assets" / "modelcases_germany_pcm_nodal_map.svg"

ZONE_COLORS = {
    "50Hertz": "#8ecae6",
    "Amprion": "#f4a261",
    "TenneT": "#98c379",
    "TransnetBW": "#c084fc",
}


def polygon_area(coords: np.ndarray) -> float:
    if len(coords) < 3:
        return 0.0
    x = coords[:, 0]
    y = coords[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def load_zone_features() -> dict[str, list[np.ndarray]]:
    data = json.loads(ZONE_GEOJSON_PATH.read_text(encoding="utf-8"))
    features: dict[str, list[np.ndarray]] = {}
    for feature in data.get("features", []):
        zone = str((feature.get("properties") or {}).get("load_zone", "")).strip()
        if not zone:
            continue
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []
        if geometry.get("type") == "Polygon":
            polygon_sets = [coords]
        elif geometry.get("type") == "MultiPolygon":
            polygon_sets = coords
        else:
            polygon_sets = []
        zone_polys: list[np.ndarray] = []
        for polygon in polygon_sets:
            if not polygon:
                continue
            outer = np.asarray(polygon[0], dtype=float)
            if len(outer) >= 3:
                zone_polys.append(outer)
        if zone_polys:
            features[zone] = zone_polys
    return features


def main() -> None:
    bus = pd.read_csv(BUS_PATH)
    line = pd.read_csv(LINE_PATH)
    bus["Longitude"] = pd.to_numeric(bus["Longitude"], errors="coerce")
    bus["Latitude"] = pd.to_numeric(bus["Latitude"], errors="coerce")
    bus = bus.dropna(subset=["Longitude", "Latitude"]).copy()

    zone_polygons = load_zone_features()
    bus_lookup = {
        str(row.Bus_id): (float(row.Longitude), float(row.Latitude))
        for row in bus.itertuples(index=False)
    }

    capacities = (
        line[["Forward Capacity (MW)", "Reverse Capacity (MW)"]]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0.0)
        .max(axis=1)
    )
    max_cap = max(float(capacities.max()), 1.0)

    fig, ax = plt.subplots(figsize=(7.2, 7.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8fafc")

    for zone, polygons in zone_polygons.items():
        base_color = ZONE_COLORS.get(zone, "#cbd5e1")
        for polygon in polygons:
            patch = Polygon(
                polygon,
                closed=True,
                facecolor=base_color,
                edgecolor=base_color,
                linewidth=0.8,
                alpha=0.18,
                joinstyle="round",
            )
            ax.add_patch(patch)

    for _, row in line.iterrows():
        from_bus = str(row["from_bus"])
        to_bus = str(row["to_bus"])
        if from_bus not in bus_lookup or to_bus not in bus_lookup:
            continue
        x0, y0 = bus_lookup[from_bus]
        x1, y1 = bus_lookup[to_bus]
        cap = max(
            float(row["Forward Capacity (MW)"]),
            float(row["Reverse Capacity (MW)"]),
        )
        width = 0.25 + 1.55 * (cap / max_cap) ** 0.6
        ax.plot([x0, x1], [y0, y1], color="#5f6f85", linewidth=width, alpha=0.52, solid_capstyle="round", zorder=2)

    zone_centers: dict[str, tuple[float, float]] = {}
    for zone, polygons in zone_polygons.items():
        largest = max(polygons, key=polygon_area)
        zone_centers[zone] = (float(largest[:, 0].mean()), float(largest[:, 1].mean()))

    ax.scatter(
        bus["Longitude"],
        bus["Latitude"],
        s=32,
        c=[ZONE_COLORS.get(str(zone), "#dbeafe") for zone in bus["Zone_id"].astype(str)],
        edgecolors="#243447",
        linewidths=0.35,
        alpha=0.92,
        zorder=3,
    )

    for zone, (x, y) in zone_centers.items():
        ax.text(x, y, zone, ha="center", va="center", fontsize=11, color="#0f172a", weight="bold", zorder=4)

    lon_pad = 0.55
    lat_pad = 0.4
    ax.set_xlim(float(bus["Longitude"].min()) - lon_pad, float(bus["Longitude"].max()) + lon_pad)
    ax.set_ylim(float(bus["Latitude"].min()) - lat_pad, float(bus["Latitude"].max()) + lat_pad)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title("Germany PCM Nodal Network View", fontsize=16, weight="bold", color="#122a4c", pad=16)
    ax.text(
        0.01,
        -0.06,
        "Geography-style nodal map with reconstructed TSO overlay from the current Germany dashboard geometry.",
        transform=ax.transAxes,
        fontsize=10,
        color="#5b697d",
        ha="left",
        va="top",
    )

    fig.tight_layout()
    fig.savefig(OUT_MAP, format="svg", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {OUT_MAP}")


if __name__ == "__main__":
    main()
