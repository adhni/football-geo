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
    assert 'marker.on("popupopen"' not in javascript
    assert 'event.target.closest(".popup-player[data-player-id]")' in javascript
    assert ".secondary-filters, .more-filters-grid { left: 0; right: auto; }" in stylesheet
    assert "thead { display: none; }" not in stylesheet


def test_nhl_explorer_reuses_the_accessible_sport_shell():
    html = (ROOT / "docs" / "nhl" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="nhl-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"NHL"' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'data-map-mode="population"' in html
    assert 'id="resolution-control"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "projectTeamSplits" in shared_javascript
    assert "filteredTeamRecords" in shared_javascript
    assert (ROOT / "docs" / "nhl" / "data" / "dashboard.json").exists()


def test_afl_explorer_uses_games_and_the_shared_accessible_shell():
    html = (ROOT / "docs" / "afl" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="afl-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"AFL"' in html
    assert 'workloadField:"games"' in html
    assert 'defaultMetric:"games"' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'data-map-mode="population"' in html
    assert 'id="resolution-control"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "EDITION.workloadField" in shared_javascript
    assert (ROOT / "docs" / "afl" / "data" / "dashboard.json").exists()


def test_nrl_explorer_uses_games_and_the_shared_accessible_shell():
    html = (ROOT / "docs" / "nrl" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="nrl-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"NRL"' in html
    assert 'workloadField:"games"' in html
    assert 'teamSplitStats:["points","tries","runMetres","tackles"]' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'data-map-mode="population"' in html
    assert 'id="resolution-control"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "EDITION.workloadField" in shared_javascript
    assert (ROOT / "docs" / "nrl" / "data" / "dashboard.json").exists()


def test_tennis_explorer_uses_points_and_population_modes():
    html = (ROOT / "docs" / "tennis" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="tennis-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Tennis"' in html
    assert 'workloadField:"points"' in html
    assert 'data-map-mode="population-workload"' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "isPopulationMode" in shared_javascript
    assert "populationMeasure" in shared_javascript
    assert (ROOT / "docs" / "tennis" / "data" / "dashboard.json").exists()


def test_padel_explorer_uses_points_and_population_modes():
    html = (ROOT / "docs" / "padel" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="padel-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Padel"' in html
    assert 'workloadField:"points"' in html
    assert 'data-map-mode="population-workload"' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "isPopulationMode" in shared_javascript
    assert "populationMeasure" in shared_javascript
    assert (ROOT / "docs" / "padel" / "data" / "dashboard.json").exists()


def test_badminton_explorer_keeps_doubles_pairs_and_uses_allocated_points():
    html = (ROOT / "docs" / "badminton" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="padel-site badminton-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Badminton"' in html
    assert 'workloadField:"points"' in html
    assert 'teamSplitStats:["points"]' in html
    assert 'teamSplitMinStats:["rank"]' in html
    assert 'data-map-mode="population-workload"' in html
    assert 'src="../assets/league-app.js"' in html
    assert html.count('role="tab"') == 4
    assert "projectedMinimums" in shared_javascript
    assert "qualityTotalWorkloadField" in shared_javascript
    assert (ROOT / "docs" / "badminton" / "data" / "dashboard.json").exists()


def test_golf_explorer_uses_two_rankings_points_and_population_modes():
    html = (ROOT / "docs" / "golf" / "index.html").read_text(encoding="utf-8")

    assert 'class="tennis-site golf-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Golf"' in html
    assert 'workloadField:"points"' in html
    assert 'data-map-mode="population-workload"' in html
    assert 'src="../assets/league-app.js"' in html
    assert html.count('role="tab"') == 4
    assert (ROOT / "docs" / "golf" / "data" / "dashboard.json").exists()


def test_cached_population_mode_restores_area_size_controls():
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    population_branch = shared_javascript.split("function updateMap()", 1)[1].split(
        "function updateKpis()", 1
    )[0]
    assert '$(".resolution-control").hidden = false;' in population_branch


def test_every_sport_switcher_links_to_racket_sports_in_order():
    pages = [ROOT / "docs" / "index.html"] + [
        ROOT / "docs" / sport / "index.html"
        for sport in ("tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb")
    ]

    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert html.count(">Padel</a>") == 1
        assert html.count(">Badminton</a>") == 1
        assert html.count(">Golf</a>") == 1
        assert html.index(">Tennis</a>") < html.index(">Padel</a>") < html.index(">Badminton</a>") < html.index(">Golf</a>")


def test_mlb_explorer_reuses_the_accessible_sport_shell():
    html = (ROOT / "docs" / "mlb" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="mlb-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"MLB"' in html
    assert 'workloadLabel:"workload"' in html
    assert 'profileOriginField:"birthCountry"' in html
    assert 'teamSplitStats:["plateAppearances"' in html
    assert 'src="../assets/league-app.js"' in html
    assert 'data-map-mode="population"' in html
    assert 'id="resolution-control"' in html
    assert 'role="tablist"' in html
    assert html.count('role="tab"') == 4
    assert "EDITION.workloadLabel" in shared_javascript
    assert (ROOT / "docs" / "mlb" / "data" / "dashboard.json").exists()
