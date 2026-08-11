from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_static_map_explorer_assets_and_controls_are_wired():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")

    for element_id in ("country-filter", "place-search", "place-options", "clear-place-search", "map-mode"):
        assert f'id="{element_id}"' in html
        assert f'$("#{element_id}")' in javascript
    assert "leaflet.markercluster@1.5.3" in html
    assert "L.markerClusterGroup" in javascript
    assert "playerList" in javascript
    assert 'id="league-comparison"' in html
    assert 'id="player-modal"' in html
    assert (ROOT / "docs" / "data" / "countries.geojson").exists()
    assert 'data-map-mode="population"' in html
    assert 'id="population-scale"' in html
    assert "POPULATION_GEO_URL" in javascript
    assert "updatePopulationMap" in javascript
    assert "populationRateColour" in javascript


def test_age_profile_controls_and_outputs_are_wired():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")

    for element_id in (
        "age-filter",
        "age-overview",
        "age-chart",
        "age-chart-mode",
        "age-group-mode",
        "youngest-players",
        "oldest-players",
        "profile-age",
    ):
        assert f'id="{element_id}"' in html
        assert f'$("#{element_id}")' in javascript
    assert 'new Date("2026-06-30T00:00:00Z")' in javascript
    assert 'exact: false' in javascript
    assert "densityBandwidth" in javascript
    assert "Silverman bandwidth" in javascript
