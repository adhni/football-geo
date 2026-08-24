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
DEFAULT_OUTPUT = ROOT / "docs" / "data" / "population_hexes_r3.geojson"
DEFAULT_CACHE = ROOT / "data" / "cache" / "worldpop_population_2025.json"
DEFAULT_COUNTRY_GEOMETRY = ROOT / "docs" / "data" / "countries.geojson"
DEFAULT_RASTER_CACHE = ROOT / "data" / "cache" / "worldpop_rasters_2025"
WORLDPOP_API = "https://api.worldpop.org/v2"
WORLDPOP_SOURCE = "WorldPop Global 2 R2025A"
WORLDPOP_MAX_H3_POLYGON_RESOLUTION = 3
WORLDPOP_COUNTRY_ALIASES = {
    "ATF": "FRA",  # French Southern Territories have no standalone WorldPop raster.
    "CYN": "CYP",
    "KOS": "SRB",
    "PSX": "PSE",
    "SAH": "MAR",  # Western Sahara is covered by the Morocco raster.
    "SDS": "SSD",
}
WORLDPOP_COUNTRY_NAME_ALIASES = {
    "American Samoa": "ASM",
    "Aruba": "ABW",
    "Curacao": "CUW",
    "Saint Lucia": "LCA",
}
WORLDPOP_TERRITORY_BOUNDS = {
    "FRO": (-7.0, 61.3, -6.0, 62.5),
    "GLP": (-61.9, 15.8, -60.9, 16.6),
    "GUF": (-54.7, 2.0, -51.5, 6.0),
    "MTQ": (-61.3, 14.3, -60.7, 14.9),
    "MYT": (44.9, -13.1, 45.4, -12.6),
    "NCL": (163.5, -23.0, 168.5, -19.0),
    "PYF": (-153.0, -28.0, -134.0, -7.0),
    "REU": (55.1, -21.5, 55.9, -20.8),
}


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
    if max(lon for lon, _ in coordinates) - min(lon for lon, _ in coordinates) > 180:
        from shapely.geometry import LineString, Polygon
        from shapely.ops import split

        shifted = Polygon([((lon + 360) if lon < 0 else lon, lat) for lon, lat in coordinates])
        pieces = split(shifted, LineString([(180, -90), (180, 90)]))
        polygons = []
        for piece in pieces.geoms:
            move_west = piece.centroid.x > 180
            ring = [
                [round((lon - 360) if move_west else lon, 6), round(lat, 6)]
                for lon, lat in piece.exterior.coords
            ]
            polygons.append([ring])
        return {"type": "MultiPolygon", "coordinates": polygons}
    return {"type": "Polygon", "coordinates": [coordinates]}


def _worldpop_raster_url(country_code: str, year: int) -> str:
    code = WORLDPOP_COUNTRY_ALIASES.get(country_code, country_code)
    filename = f"{code.lower()}_pop_{year}_CN_1km_R2025A_UA_v1.tif"
    return (
        "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/"
        f"{year}/{code}/v1/1km_ua/constrained/{filename}"
    )


def _download_worldpop_raster(country_code: str, year: int, raster_cache_dir: Path) -> Path:
    code = WORLDPOP_COUNTRY_ALIASES.get(country_code, country_code)
    path = raster_cache_dir / f"{code}_{year}.tif"
    if path.exists():
        return path
    raster_cache_dir.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tif.tmp")
    with requests.get(
        _worldpop_raster_url(code, year),
        timeout=180,
        stream=True,
        headers={"User-Agent": "TalentGeography/1.0"},
    ) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)
    temporary.replace(path)
    return path


def _cell_country_codes(
    cell_ids: Iterable[str],
    country_geometry_path: Path,
    hinted_countries: dict[str, Iterable[str]] | None = None,
) -> dict[str, list[str]]:
    from shapely.geometry import box, shape

    countries = json.loads(country_geometry_path.read_text(encoding="utf-8"))["features"]
    geometries = [
        (WORLDPOP_COUNTRY_ALIASES.get(feature["properties"]["ADM0_A3"], feature["properties"]["ADM0_A3"]), shape(feature["geometry"]))
        for feature in countries
    ]
    name_codes = {}
    for feature in countries:
        code = WORLDPOP_COUNTRY_ALIASES.get(
            feature["properties"]["ADM0_A3"], feature["properties"]["ADM0_A3"]
        )
        for field in ("ADMIN", "NAME", "NAME_LONG", "FORMAL_EN", "BRK_NAME", "SOVEREIGNT"):
            if feature["properties"].get(field):
                name_codes.setdefault(str(feature["properties"][field]), code)
    name_codes.update(WORLDPOP_COUNTRY_NAME_ALIASES)
    output = {}
    for cell_id in cell_ids:
        cell = shape(cell_polygon(cell_id))
        codes = {code for code, geometry in geometries if geometry.intersects(cell)}
        codes.update(
            code for code, bounds in WORLDPOP_TERRITORY_BOUNDS.items()
            if cell.intersects(box(*bounds))
        )
        codes.update(
            name_codes[name]
            for name in (hinted_countries or {}).get(cell_id, [])
            if name in name_codes
        )
        output[cell_id] = sorted(codes)
    return output


def population_from_rasters(
    cell_ids: Iterable[str],
    *,
    year: int,
    country_geometry_path: Path,
    raster_cache_dir: Path,
    workers: int = 4,
    hinted_countries: dict[str, Iterable[str]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Calculate coarse-cell population directly from official 1 km rasters."""
    import numpy as np
    import rasterio
    from rasterio.mask import mask

    cell_ids = sorted(cell_ids)
    country_codes = _cell_country_codes(cell_ids, country_geometry_path, hinted_countries)
    required = sorted({code for codes in country_codes.values() for code in codes})
    print(f"Preparing {len(required):,} WorldPop country rasters for {len(cell_ids):,} occupied areas...", flush=True)
    rasters: dict[str, Path] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_download_worldpop_raster, code, year, raster_cache_dir): code
            for code in required
        }
        for index, future in enumerate(as_completed(futures), start=1):
            code = futures[future]
            rasters[code] = future.result()
            if index % 10 == 0 or index == len(required):
                print(f"  prepared {index:,}/{len(required):,} country rasters", flush=True)

    results = {}
    for index, cell_id in enumerate(cell_ids, start=1):
        geometry = cell_polygon(cell_id)
        population = 0.0
        for code in country_codes[cell_id]:
            with rasterio.open(rasters[code]) as source:
                try:
                    values, _ = mask(source, [geometry], crop=True, filled=False)
                except ValueError:
                    continue
                population += float(np.ma.filled(np.ma.sum(values[0]), 0))
        area_km2 = float(h3.cell_area(cell_id, unit="km^2"))
        results[cell_id] = {
            "population": round(population),
            "area_km2": round(area_km2, 1),
            "population_density": round(population / area_km2, 1) if area_km2 else 0,
            "data_year": year,
            "data_source": WORLDPOP_SOURCE,
        }
        if index % 10 == 0 or index == len(cell_ids):
            print(f"  calculated {index:,}/{len(cell_ids):,} occupied areas", flush=True)
    return results


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
    country_geometry_path: Path = DEFAULT_COUNTRY_GEOMETRY,
    raster_cache_dir: Path = DEFAULT_RASTER_CACHE,
    use_rasters: bool = False,
) -> dict[str, Any]:
    cells = occupied_hexes(payload, h3_resolution)
    raster_population = None
    query_cells = sorted(cells)
    if use_rasters or h3_resolution < WORLDPOP_MAX_H3_POLYGON_RESOLUTION:
        raster_population = population_from_rasters(
            cells,
            year=year,
            country_geometry_path=country_geometry_path,
            raster_cache_dir=raster_cache_dir,
            workers=workers,
            hinted_countries={cell_id: cell["countries"].keys() for cell_id, cell in cells.items()},
        )
    cache: dict[str, dict[str, Any]] = {}
    if raster_population is None and cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    missing = [
        cell_id for cell_id in query_cells
        if population_cache_key(cell_id, year, raster_resolution) not in cache
    ] if raster_population is None else []
    if missing:
        print(
            f"Querying WorldPop for {len(missing):,} of {len(query_cells):,} population cells "
            f"covering {len(cells):,} occupied areas...",
            flush=True,
        )
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
        population = raster_population[cell_id] if raster_population is not None else cache[
            population_cache_key(cell_id, year, raster_resolution)
        ]
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
            "population_method": "official_country_rasters" if raster_population is not None else "polygon_api",
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
    country_geometry_path: Path = DEFAULT_COUNTRY_GEOMETRY,
    raster_cache_dir: Path = DEFAULT_RASTER_CACHE,
    use_rasters: bool = False,
) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    result = build_population_hexes(
        payload,
        cache_path=cache_path,
        year=year,
        h3_resolution=h3_resolution,
        workers=workers,
        country_geometry_path=country_geometry_path,
        raster_cache_dir=raster_cache_dir,
        use_rasters=use_rasters,
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
    parser.add_argument("--country-geometry", type=Path, default=DEFAULT_COUNTRY_GEOMETRY)
    parser.add_argument("--raster-cache", type=Path, default=DEFAULT_RASTER_CACHE)
    parser.add_argument("--use-rasters", action="store_true", help="Use official country rasters instead of the polygon API")
    args = parser.parse_args()
    run(
        input_path=args.input,
        output_path=args.output,
        cache_path=args.cache,
        year=args.year,
        h3_resolution=args.h3_resolution,
        workers=args.workers,
        country_geometry_path=args.country_geometry,
        raster_cache_dir=args.raster_cache,
        use_rasters=args.use_rasters,
    )


if __name__ == "__main__":
    main()
