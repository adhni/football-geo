import json
from pathlib import Path

import pytest

from src.ftg.build_population_hexes import (
    WORLDPOP_COUNTRY_NAME_ALIASES,
    build_population_hexes,
    cell_polygon,
    occupied_hexes,
    population_cache_key,
)


ROOT = Path(__file__).resolve().parents[1]


def test_small_caribbean_territories_use_their_official_worldpop_rasters():
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Aruba"] == "ABW"
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Barbados"] == "BRB"
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Curacao"] == "CUW"
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Grenada"] == "GRD"
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Saint Kitts and Nevis"] == "KNA"


def test_small_pacific_islands_use_their_official_worldpop_rasters():
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Samoa"] == "WSM"
    assert WORLDPOP_COUNTRY_NAME_ALIASES["Tonga"] == "TON"


def test_occupied_hexes_deduplicates_players_and_keeps_nearby_places_together():
    payload = {
        "records": [
            {"id": "p1", "mapped": True, "lat": 51.5072, "lon": -0.1276, "place": "London", "country": "United Kingdom"},
            {"id": "p1", "mapped": True, "lat": 51.5072, "lon": -0.1276, "place": "London", "country": "United Kingdom"},
            {"id": "p2", "mapped": True, "lat": 51.52, "lon": -0.1, "place": "London", "country": "United Kingdom"},
            {"id": "p4", "mapped": True, "locationType": "football_origin", "lat": 51.52, "lon": -0.1, "place": "London club", "country": "United Kingdom"},
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


@pytest.mark.parametrize("sport", ["football", "cricket", "ufc", "formula", "motogp", "volleyball", "tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb"])
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
    expected = dashboard["summary"].get("birthplace_mapped_players", dashboard["summary"]["mapped_players"])
    assert sum(feature["properties"]["all_players"] for feature in population["features"]) == expected
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


def _raster_payload():
    return {"records": [
        {"id": "p1", "mapped": True, "lat": 51.5, "lon": -.1, "country": "United Kingdom"},
        {"id": "p2", "mapped": True, "lat": 48.8, "lon": 2.3, "country": "France"},
    ]}


def _population_result(year=2025):
    return {"population": 100000, "area_km2": 10, "population_density": 10000,
            "data_year": year, "data_source": "test"}


def test_raster_cache_reuses_totals_but_rebuilds_player_membership(tmp_path, monkeypatch):
    calls = []

    def calculate(cells, *, on_result, year, **kwargs):
        calls.append(list(cells))
        for cell in cells:
            on_result(cell, _population_result(year))

    monkeypatch.setattr("src.ftg.build_population_hexes.population_from_rasters", calculate)
    payload = _raster_payload()
    cache = tmp_path / "population.json"
    first = build_population_hexes(payload, cache_path=cache, use_rasters=True)
    payload["records"][0]["id"] = "replacement"
    second = build_population_hexes(payload, cache_path=cache, use_rasters=True)
    assert len(calls) == 1
    assert first["metadata"] == second["metadata"]
    ids = {player for feature in second["features"] for player in feature["properties"]["player_ids"]}
    assert ids == {"replacement", "p2"}
    assert second["metadata"]["population_method"] == "official_country_rasters"


def test_raster_cache_resumes_completed_cells_after_failure(tmp_path, monkeypatch):
    calls = []
    completed = []

    def calculate(cells, *, on_result, **kwargs):
        calls.append(list(cells))
        for cell in cells:
            on_result(cell, _population_result())
            completed.append(cell)
            if len(calls) == 1:
                raise RuntimeError("Interrupted after one cell")

    monkeypatch.setattr("src.ftg.build_population_hexes.population_from_rasters", calculate)
    cache = tmp_path / "population.json"
    with pytest.raises(RuntimeError, match="Interrupted"):
        build_population_hexes(_raster_payload(), cache_path=cache, use_rasters=True)
    result = build_population_hexes(_raster_payload(), cache_path=cache, use_rasters=True)
    assert len(calls[0]) == 2
    assert len(calls[1]) == 1
    assert completed[0] not in calls[1]
    assert result["metadata"]["mapped_players"] == 2


@pytest.mark.parametrize("change", ["year", "h3", "source", "geometry", "hints", "refresh"])
def test_raster_cache_invalidates_changed_inputs(tmp_path, monkeypatch, change):
    from src.ftg import build_population_hexes as builder

    calls = []

    def calculate(cells, *, on_result, year, **kwargs):
        calls.append(list(cells))
        for cell in cells:
            on_result(cell, _population_result(year))

    monkeypatch.setattr(builder, "population_from_rasters", calculate)
    geometry = tmp_path / "countries.geojson"
    geometry.write_text('{"features":[]}')
    payload = _raster_payload()
    options = {"cache_path": tmp_path / "population.json", "use_rasters": True, "country_geometry_path": geometry}
    builder.build_population_hexes(payload, **options)
    if change == "year":
        options["year"] = 2024
    elif change == "h3":
        options["h3_resolution"] = 2
    elif change == "source":
        monkeypatch.setattr(builder, "WORLDPOP_SOURCE", "New release")
    elif change == "geometry":
        geometry.write_text('{"features":[],"version":2}')
    elif change == "hints":
        payload["records"][0]["country"] = "Changed hint"
    else:
        options["refresh_population"] = True
    builder.build_population_hexes(payload, **options)
    assert len(calls) == 2
    assert len(calls[1]) == (1 if change == "hints" else 2)


def test_api_cache_entries_are_not_used_for_raster_totals(tmp_path, monkeypatch):
    payload = _raster_payload()
    cache = tmp_path / "population.json"
    cache.write_text(json.dumps({population_cache_key(cell, 2025, "1km"): _population_result()
                                 for cell in occupied_hexes(payload)}))

    def calculate(cells, *, on_result, **kwargs):
        for cell in cells:
            on_result(cell, {**_population_result(), "population": 200000})

    monkeypatch.setattr("src.ftg.build_population_hexes.population_from_rasters", calculate)
    result = build_population_hexes(payload, cache_path=cache, use_rasters=True)
    assert all(feature["properties"]["population"] == 200000 for feature in result["features"])


def test_raster_files_are_reused_and_closed(tmp_path, monkeypatch):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from src.ftg import build_population_hexes as builder

    path = tmp_path / "population.tif"
    with rasterio.open(path, "w", driver="GTiff", height=100, width=100, count=1,
                       dtype="float32", crs="EPSG:4326", transform=from_origin(-5, 56, .1, .1)) as output:
        output.write(np.ones((1, 100, 100), dtype="float32"))
    cells = list(occupied_hexes(_raster_payload()))
    monkeypatch.setattr(builder, "_cell_country_codes", lambda *args: {cell: ["TEST"] for cell in cells})
    monkeypatch.setattr(builder, "_download_worldpop_raster", lambda *args: path)
    real_open = rasterio.open
    opened = []

    def track_open(*args, **kwargs):
        source = real_open(*args, **kwargs)
        opened.append(source)
        return source

    monkeypatch.setattr(rasterio, "open", track_open)
    result = builder.population_from_rasters(cells, year=2025, country_geometry_path=path, raster_cache_dir=tmp_path)
    assert len(opened) == 1
    assert opened[0].closed
    assert all(value["population"] > 0 for value in result.values())
