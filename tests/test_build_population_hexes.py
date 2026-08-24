import json
from pathlib import Path

import pytest

from src.ftg.build_population_hexes import (
    build_population_hexes,
    cell_polygon,
    occupied_hexes,
    population_cache_key,
)


ROOT = Path(__file__).resolve().parents[1]


def test_occupied_hexes_deduplicates_players_and_keeps_nearby_places_together():
    payload = {
        "records": [
            {"id": "p1", "mapped": True, "lat": 51.5072, "lon": -0.1276, "place": "London", "country": "United Kingdom"},
            {"id": "p1", "mapped": True, "lat": 51.5072, "lon": -0.1276, "place": "London", "country": "United Kingdom"},
            {"id": "p2", "mapped": True, "lat": 51.52, "lon": -0.1, "place": "London", "country": "United Kingdom"},
            {"id": "p3", "mapped": False, "lat": None, "lon": None, "place": None, "country": None},
        ]
    }

    cells = occupied_hexes(payload, resolution=3)

    assert len(cells) == 1
    assert sorted(next(iter(cells.values()))["player_ids"]) == ["p1", "p2"]


def test_cell_polygon_is_closed_geojson():
    cell_id = next(iter(occupied_hexes({"records": [{"id": "p1", "mapped": True, "lat": 51.5, "lon": -.1}]}, 3)))
    geometry = cell_polygon(cell_id)

    assert geometry["type"] == "Polygon"
    assert geometry["coordinates"][0][0] == geometry["coordinates"][0][-1]
    json.dumps(geometry)


def test_cell_polygon_splits_antimeridian_cells():
    geometry = cell_polygon("81bb3ffffffffff")

    assert geometry["type"] == "MultiPolygon"
    assert all(
        max(point[0] for point in polygon[0]) - min(point[0] for point in polygon[0]) < 180
        for polygon in geometry["coordinates"]
    )


@pytest.mark.parametrize("sport", ["football", "nba", "nfl", "nhl"])
@pytest.mark.parametrize("resolution", [1, 2, 3])
def test_published_sport_population_layers_match_mapped_player_scope(sport, resolution):
    directory = ROOT / "docs" if sport == "football" else ROOT / "docs" / sport
    population = json.loads((directory / "data" / f"population_hexes_r{resolution}.geojson").read_text(encoding="utf-8"))
    dashboard = json.loads((directory / "data" / "dashboard.json").read_text(encoding="utf-8"))

    assert population["type"] == "FeatureCollection"
    assert population["metadata"]["population_year"] == 2025
    assert population["metadata"]["raster_resolution"] == "1km"
    assert population["metadata"]["h3_resolution"] == resolution
    assert population["metadata"]["population_method"] == "official_country_rasters"
    assert sum(feature["properties"]["all_players"] for feature in population["features"]) == dashboard["summary"]["mapped_players"]
    assert all(feature["properties"]["population"] > 0 for feature in population["features"])


def test_population_cache_is_scoped_by_year_and_raster_resolution(tmp_path, monkeypatch):
    payload = {"records": [{"id": "p1", "mapped": True, "lat": 51.5, "lon": -.1, "place": "London", "country": "United Kingdom"}]}
    calls = []

    def fake_population(cell_id, year, resolution):
        calls.append((cell_id, year, resolution))
        return {"population": year, "area_km2": 1, "population_density": 1, "data_year": year, "data_source": "test"}

    monkeypatch.setattr("src.ftg.build_population_hexes._request_population", fake_population)
    cache_path = tmp_path / "population.json"

    first = build_population_hexes(payload, cache_path=cache_path, year=2024, raster_resolution="1km", workers=1)
    second = build_population_hexes(payload, cache_path=cache_path, year=2025, raster_resolution="1km", workers=1)

    assert first["features"][0]["properties"]["population"] == 2024
    assert second["features"][0]["properties"]["population"] == 2025
    assert [call[1] for call in calls] == [2024, 2025]
    assert population_cache_key(calls[0][0], 2024, "1km") != population_cache_key(calls[0][0], 2025, "1km")
