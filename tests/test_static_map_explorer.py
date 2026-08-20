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
    assert "Smoothed age distribution" in javascript
    assert "Silverman bandwidth" not in javascript


def test_friendlier_dashboard_structure_and_accessibility_are_wired():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    stylesheet = (ROOT / "docs" / "assets" / "styles.css").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")

    for element_id in (
        "main-content",
        "more-filters",
        "active-filters",
        "load-more-players",
        "player-empty-state",
    ):
        assert f'id="{element_id}"' in html

    assert 'class="skip-link"' in html
    assert 'href="./favicon.svg"' in html
    assert (ROOT / "docs" / "favicon.svg").exists()
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert 'data-view="age"' not in html
    assert "Birthplace is not the same as where a player grew up or developed" in html

    for selector in (
        ".skip-link",
        ".active-filters",
        ".filter-chip",
        ".empty-state",
        ".load-more-button",
        ":focus-visible",
    ):
        assert selector in stylesheet

    for behaviour in (
        "playerLimit: 150",
        "updateActiveFilters",
        "handleModalKeydown",
        "loadPopulationGeometry",
        "countryMetadataAvailable",
        "filteredRecords({ ignoreAge: true })",
        'class="player-open-button"',
        'role="img" aria-label=',
        "setBackgroundInert(true)",
        "setBackgroundInert(false)",
        '$("#load-more-players")',
        'setAttribute("aria-selected"',
    ):
        assert behaviour in javascript

    assert 'class="player-row" data-player-id=' not in javascript
    assert ".secondary-filters, .more-filters-grid { left: 0; right: auto; }" in stylesheet
    assert "thead { display: none; }" not in stylesheet
