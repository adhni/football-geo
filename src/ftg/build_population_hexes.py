from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import h3
import requests

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "docs" / "data" / "dashboard.json"
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "population_hexes.geojson"
DEFAULT_CACHE = ROOT / "data" / "cache" / "worldpop_population_2025.json"
WORLDPOP_API = "https://api.worldpop.org/v2"
WORLDPOP_SOURCE = "WorldPop Global 2 R2025A"


def population_cache_key(cell_id: str, year: int, resolution: str) -> str:
    return f"{year}:{resolution}:{cell_id}"


def occupied_hexes(payload: dict[str, Any], resolution: int = 3) -> dict[str, dict[str, Any]]:
    """Assign each mapped player once to an H3 cell."""
    players: dict[str, dict[str, Any]] = {}
    for row in payload["records"]:
        if not row.get("mapped") or row.get("lat") is None or row.get("lon") is None:
            continue
        players.setdefault(str(row["id"]), row)

    cells: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"player_ids": [], "places": Counter(), "countries": Counter()}
    )
    for player_id, row in players.items():
        cell_id = h3.latlng_to_cell(float(row["lat"]), float(row["lon"]), resolution)
        cell = cells[cell_id]
        cell["player_ids"].append(player_id)
        if row.get("place"):
            cell["places"][str(row["place"])] += 1
        if row.get("country"):
            cell["countries"][str(row["country"])] += 1
    return dict(cells)


def cell_polygon(cell_id: str) -> dict[str, Any]:
    boundary = h3.cell_to_boundary(cell_id)
    coordinates = [[round(lon, 6), round(lat, 6)] for lat, lon in boundary]
    coordinates.append(coordinates[0])
    return {"type": "Polygon", "coordinates": [coordinates]}


def _request_population(
    cell_id: str,
    year: int,
    resolution: str,
    timeout: float = 45,
    attempts: int = 4,
) -> dict[str, Any]:
    payload = {"geojson": cell_polygon(cell_id), "year": year, "resolution": resolution}
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.post(f"{WORLDPOP_API}/population", json=payload, timeout=timeout)
            response.raise_for_status()
            task_id = response.json()["task_id"]
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                status_response = requests.get(f"{WORLDPOP_API}/tasks/{task_id}", timeout=timeout)
                status_response.raise_for_status()
                status = status_response.json()
                if status["status"].lower() == "success":
                    result = status["result"]
                    return {
                        "population": round(float(result["total_population"])),
                        "area_km2": round(float(result["area_km2"]), 1),
                        "population_density": round(float(result["population_density"]), 1),
                        "data_year": int(result["data_year"]),
                        "data_source": str(result["data_source"]),
                    }
                if status["status"].lower() == "failure":
                    raise RuntimeError(status.get("error") or "WorldPop task failed")
                time.sleep(.35)
            raise TimeoutError(f"WorldPop task {task_id} did not finish")
        except (requests.RequestException, KeyError, TypeError, ValueError, RuntimeError, TimeoutError) as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Population lookup failed for {cell_id}: {last_error}")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def build_population_hexes(
    payload: dict[str, Any],
    *,
    cache_path: Path,
    year: int = 2025,
    h3_resolution: int = 3,
    raster_resolution: str = "1km",
    workers: int = 4,
) -> dict[str, Any]:
    cells = occupied_hexes(payload, h3_resolution)
    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    missing = [
        cell_id for cell_id in cells
        if population_cache_key(cell_id, year, raster_resolution) not in cache
    ]
    if missing:
        print(f"Querying WorldPop for {len(missing):,} of {len(cells):,} occupied cells...", flush=True)
        errors: list[str] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_request_population, cell_id, year, raster_resolution): cell_id
                for cell_id in missing
            }
            for index, future in enumerate(as_completed(futures), start=1):
                cell_id = futures[future]
                try:
                    result = future.result()
                except RuntimeError as error:
                    errors.append(str(error))
                    print(f"  failed {cell_id}: {error}", flush=True)
                else:
                    cache[population_cache_key(cell_id, year, raster_resolution)] = result
                    if index % 10 == 0 or index == len(missing):
                        _write_json(cache_path, cache)
                        print(f"  processed {index:,}/{len(missing):,} · cached {len(cache):,}", flush=True)
        _write_json(cache_path, cache)
        if errors:
            raise RuntimeError(f"WorldPop failed for {len(errors)} cells; cached results are safe to resume")

    features = []
    for cell_id, cell in cells.items():
        population = cache[population_cache_key(cell_id, year, raster_resolution)]
        player_ids = sorted(cell["player_ids"])
        players_per_million = len(player_ids) / population["population"] * 1_000_000 if population["population"] else None
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "hex_id": cell_id,
                    "population": population["population"],
                    "population_year": population["data_year"],
                    "area_km2": population["area_km2"],
                    "population_density": population["population_density"],
                    "all_players": len(player_ids),
                    "players_per_million": round(players_per_million, 2) if players_per_million is not None else None,
                    "player_ids": player_ids,
                    "label": cell["places"].most_common(1)[0][0] if cell["places"] else "Mapped area",
                    "country": cell["countries"].most_common(1)[0][0] if cell["countries"] else "",
                },
                "geometry": cell_polygon(cell_id),
            }
        )
    features.sort(key=lambda feature: feature["properties"]["hex_id"])
    return {
        "type": "FeatureCollection",
        "metadata": {
            "population_source": WORLDPOP_SOURCE,
            "population_source_url": "https://hub.worldpop.org/project/categories?id=3",
            "population_license": "CC BY 4.0",
            "population_year": year,
            "raster_resolution": raster_resolution,
            "h3_resolution": h3_resolution,
            "occupied_cells": len(features),
            "mapped_players": sum(feature["properties"]["all_players"] for feature in features),
        },
        "features": features,
    }


def run(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    cache_path: Path = DEFAULT_CACHE,
    year: int = 2025,
    h3_resolution: int = 3,
    workers: int = 4,
) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    result = build_population_hexes(
        payload,
        cache_path=cache_path,
        year=year,
        h3_resolution=h3_resolution,
        workers=workers,
    )
    _write_json(output_path, result)
    print(
        f"Wrote {result['metadata']['occupied_cells']:,} occupied cells and "
        f"{result['metadata']['mapped_players']:,} mapped players to {output_path}"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build population-normalized H3 cells for the static map")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--h3-resolution", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run(args.input, args.output, args.cache, args.year, args.h3_resolution, args.workers)


if __name__ == "__main__":
    main()
