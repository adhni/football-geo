from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_static_map_explorer_assets_and_controls_are_wired():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")

    for element_id in ("country-filter", "place-search", "place-options", "clear-place-search"):
        assert f'id="{element_id}"' in html
        assert f'$("#{element_id}")' in javascript
    assert "leaflet.markercluster@1.5.3" in html
    assert "L.markerClusterGroup" in javascript
    assert "playerList" in javascript
