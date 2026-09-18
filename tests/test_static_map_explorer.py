import json
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


def test_cricket_explorer_uses_appearances_and_two_competitions():
    html = (ROOT / "docs" / "cricket" / "index.html").read_text(encoding="utf-8")

    assert 'class="padel-site cricket-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Cricket"' in html
    assert 'workloadField:"appearances"' in html
    assert 'teamSplitStats:["appearances","runs","wickets","catches","playerOfMatch"]' in html
    assert 'profileStats:["appearances","runs","wickets","catches","playerOfMatch"]' in html
    assert 'data-map-mode="population-workload"' in html
    assert '>Appearances per 1M</button>' in html
    assert 'src="../assets/league-app.js"' in html
    assert html.count('role="tab"') == 4
    assert (ROOT / "docs" / "cricket" / "data" / "dashboard.json").exists()


def test_ufc_explorer_uses_bouts_and_labels_fighter_origins():
    html = (ROOT / "docs" / "ufc" / "index.html").read_text(encoding="utf-8")
    assert 'class="ufc-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"UFC"' in html
    assert 'workloadField:"bouts"' in html
    assert 'originLabel:"Fighter origin"' in html
    assert 'data-map-mode="population-workload"' in html
    assert '>Bouts per 1M</button>' in html
    assert 'id="profile-fight-log"' in html
    assert 'src="../assets/league-app.js"' in html
    assert html.count('role="tab"') == 4
    assert (ROOT / "docs" / "ufc" / "data" / "dashboard.json").exists()


def test_formula_explorer_uses_laps_and_includes_all_four_series():
    html = (ROOT / "docs" / "formula" / "index.html").read_text(encoding="utf-8")
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    assert 'class="formula-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Formula"' in html
    assert 'workloadField:"laps"' in html
    assert 'participantLabelPlural:"drivers"' in html
    assert 'profileLogType:"race"' in html
    assert 'data-map-mode="population-workload"' in html
    assert '>Laps per 1M</button>' in html
    assert 'id="profile-event-log"' in html
    assert 'src="../assets/league-app.js"' in html
    assert html.count('role="tab"') == 4
    assert "player.raceLog" in shared_javascript
    assert (ROOT / "docs" / "formula" / "data" / "dashboard.json").exists()


def test_motogp_explorer_uses_laps_and_includes_all_five_series():
    html = (ROOT / "docs" / "motogp" / "index.html").read_text(encoding="utf-8")

    assert 'class="motogp-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"MotoGP"' in html
    assert 'workloadField:"laps"' in html
    assert 'participantLabelPlural:"riders"' in html
    assert 'profileLogType:"race"' in html
    assert '>Laps per 1M</button>' in html
    assert all(series in html for series in ("MotoGP", "Moto2", "Moto3", "MotoE", "WorldWCR"))
    assert html.count('role="tab"') == 4
    assert (ROOT / "docs" / "motogp" / "data" / "dashboard.json").exists()


def test_volleyball_explorer_uses_sets_and_includes_women_and_men():
    html = (ROOT / "docs" / "volleyball" / "index.html").read_text(encoding="utf-8")

    assert 'class="volleyball-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Volleyball"' in html
    assert 'workloadField:"sets"' in html
    assert 'profileLogType:"volleyball"' in html
    assert '>Sets per 1M</button>' in html
    assert "women&apos;s and men&apos;s" in html
    assert html.count('role="tab"') == 4
    assert (ROOT / "docs" / "volleyball" / "data" / "dashboard.json").exists()


def test_athletics_explorer_uses_event_entries_and_all_tokyo_events():
    html = (ROOT / "docs" / "athletics" / "index.html").read_text(encoding="utf-8")
    payload = json.loads((ROOT / "docs" / "athletics" / "data" / "dashboard.json").read_text(encoding="utf-8"))

    assert 'class="athletics-site"' in html
    assert 'window.TALENT_GEO_EDITION={name:"Athletics"' in html
    assert 'workloadField:"entries"' in html
    assert 'profileLogType:"athletics"' in html
    assert 'positionValuesField:"eventNames"' in html
    assert 'participantDetailField:"eventNames"' in html
    assert 'popupDetailField:"eventNames"' in html
    assert '<label for="position-filter">Event</label>' in html
    assert '<option value="all">All events</option>' in html
    assert '>Entries per 1M</button>' in html
    assert html.count('role="tab"') == 4
    assert payload["summary"]["events"] == 49
    assert payload["summary"]["players"] == 1992
    assert payload["summary"]["entries"] == 2274
    assert all(record["eventNames"] for record in payload["records"])
    assert "positionValues(row)" in (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")


def test_every_sport_has_a_primary_workload_population_mode():
    expected = {
        "index.html": "Starts per 1M",
        "afl/index.html": "Games per 1M",
        "nrl/index.html": "Games per 1M",
        "nba/index.html": "Minutes per 1M",
        "nfl/index.html": "Snaps per 1M",
        "nhl/index.html": "Minutes per 1M",
        "mlb/index.html": "Workload per 1M",
        "tennis/index.html": "Points per 1M",
        "padel/index.html": "Points per 1M",
        "badminton/index.html": "Points per 1M",
        "golf/index.html": "Points per 1M",
        "cricket/index.html": "Appearances per 1M",
        "ufc/index.html": "Bouts per 1M",
        "formula/index.html": "Laps per 1M",
        "motogp/index.html": "Laps per 1M",
        "volleyball/index.html": "Sets per 1M",
        "athletics/index.html": "Entries per 1M",
    }

    for relative_path, label in expected.items():
        html = (ROOT / "docs" / relative_path).read_text(encoding="utf-8")
        assert 'data-map-mode="population-workload"' in html
        assert f">{label}</button>" in html

    football_javascript = (ROOT / "docs" / "assets" / "app.js").read_text(encoding="utf-8")
    nfl_javascript = (ROOT / "docs" / "nfl" / "app.js").read_text(encoding="utf-8")
    for javascript, workload in ((football_javascript, "starts"), (nfl_javascript, "snaps")):
        assert "function isPopulationMode()" in javascript
        assert "function populationMeasure()" in javascript
        assert f'row.{workload}' in javascript


def test_cached_population_mode_restores_area_size_controls():
    shared_javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")

    population_branch = shared_javascript.split("function updateMap()", 1)[1].split(
        "function updateKpis()", 1
    )[0]
    assert '$(".resolution-control").hidden = false;' in population_branch


def test_every_sport_uses_the_central_navigation_registry():
    pages = [ROOT / "docs" / "index.html"] + [
        ROOT / "docs" / sport / "index.html"
        for sport in ("cricket", "ufc", "formula", "motogp", "volleyball", "athletics", "tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb")
    ]

    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert '<nav class="sport-switcher" aria-label="Choose a sport"></nav>' in html
        assert "assets/sport-navigation.js" in html

    navigation = (ROOT / "docs" / "assets" / "sport-navigation.js").read_text(encoding="utf-8")
    expected_order = ("football", "cricket", "ufc", "formula", "motogp", "volleyball", "athletics", "tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb")
    offsets = [navigation.index(f'id: "{sport}"') for sport in expected_order]
    assert offsets == sorted(offsets)
    assert "readMapState" in navigation
    assert "comparisonUrl" in navigation
    assert "mountMapSwitcher" in navigation
    assert "restoreMapScroll" in navigation
    assert 'data-sport-id=' in navigation
    assert "mapStateReader" in navigation
    assert 'url.hash = "map"' in navigation


def test_all_sports_directory_explains_comparison_scope():
    html = (ROOT / "docs" / "sports" / "index.html").read_text(encoding="utf-8")
    stylesheet = (ROOT / "docs" / "sports" / "sports.css").read_text(encoding="utf-8")

    assert 'id="sport-directory"' in html
    assert "Seventeen sporting lenses" in html
    assert "workload measures retain their sport-specific meanings" in html
    assert "TalentGeoNavigation.renderDirectory" in html
    assert ".sport-directory" in stylesheet


def test_cross_sport_comparison_has_synchronised_maps_and_independent_measures():
    html = (ROOT / "docs" / "compare" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "compare" / "compare.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "docs" / "compare" / "compare.css").read_text(encoding="utf-8")
    navigation = (ROOT / "docs" / "assets" / "sport-navigation.js").read_text(encoding="utf-8")

    for element_id in (
        "left-sport",
        "right-sport",
        "left-map",
        "right-map",
        "view-mode",
        "resolution-control",
        "swap-sports",
        "copy-link",
    ):
        assert f'id="{element_id}"' in html

    assert 'data-preset="nfl,nba"' in html
    assert 'data-preset="afl,nrl"' in html
    assert 'data-preset="tennis,golf"' in html
    assert 'role="tablist"' in html
    assert "function syncViewport(sourceSide)" in javascript
    assert "target.setView(source.getCenter(), source.getZoom()" in javascript
    assert "function populationCells(" in javascript
    assert 'record.locationType === "birthplace"' in javascript
    assert "leftMeasure" in javascript and "rightMeasure" in javascript
    assert ".compare-grid" in stylesheet
    assert ".active-mobile-panel" in stylesheet
    assert "sideBySideUrl" in navigation
    assert 'href="../compare/' in (ROOT / "docs" / "sports" / "index.html").read_text(encoding="utf-8")


def test_comparison_registry_workload_fields_exist_in_every_payload():
    payload_paths = {"football": ROOT / "docs" / "data" / "dashboard.json"}
    payload_paths.update({
        sport: ROOT / "docs" / sport / "data" / "dashboard.json"
        for sport in ("cricket", "ufc", "formula", "motogp", "volleyball", "athletics", "tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb")
    })
    workload_fields = {
        "football": "starts", "cricket": "appearances", "ufc": "bouts",
        "formula": "laps", "motogp": "laps", "volleyball": "sets", "athletics": "entries",
        "tennis": "points", "padel": "points", "badminton": "points",
        "golf": "points", "afl": "games", "nrl": "games", "nba": "minutes",
        "nfl": "snaps", "nhl": "minutes", "mlb": "minutes",
    }

    for sport, path in payload_paths.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["records"]
        assert all(workload_fields[sport] in record for record in payload["records"])


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


def test_nfl_college_lens_is_separate_and_disables_population_rates():
    html = (ROOT / "docs" / "nfl" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "nfl" / "app.js").read_text(encoding="utf-8")
    payload = json.loads((ROOT / "docs" / "nfl" / "data" / "dashboard.json").read_text(encoding="utf-8"))

    assert 'data-location-lens="college"' in html
    assert 'id="profile-college"' in html
    assert 'button.disabled = college' in javascript
    assert 'state.locationLens === "college" && isPopulationMode()' in javascript
    assert payload["summary"]["college_player_coverage_pct"] >= 95
    assert sum(row["snaps"] for row in payload["records"] if row["collegeMapped"]) == payload["summary"]["college_mapped_snaps"]
    assert len({row["id"] for row in payload["records"]}) == payload["summary"]["players"]


def test_nfl_population_map_preserves_reference_cells():
    javascript = (ROOT / "docs" / "nfl" / "app.js").read_text(encoding="utf-8")

    assert "reference: !selected.length" in javascript
    assert "if (cell.reference)" in javascript
    assert "activeCount" in javascript
    assert "referenceCount" in javascript
    assert "cells.filter((cell) => !cell.reference)" in javascript


def test_ufc_population_rebuild_preserves_reference_cells():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ufc_command = readme.split("To refresh the complete calendar-year 2025 UFC snapshot:", 1)[1].split("```", 2)[1]

    assert "--use-rasters" in ufc_command
    assert "--include-reference-cells" in ufc_command


def test_nfl_multi_team_picker_renders_team_rosettes():
    html = (ROOT / "docs" / "nfl" / "index.html").read_text(encoding="utf-8")
    javascript = (ROOT / "docs" / "nfl" / "app.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "docs" / "nfl" / "nfl.css").read_text(encoding="utf-8")

    assert 'id="team-picker"' in html
    assert 'aria-label="Choose up to six teams"' in html
    assert 'id="team-colour-legend"' in html
    assert "const TEAM_COLOURS" in javascript
    assert "function aggregateTeamPlaces(records)" in javascript
    assert "function renderTeamCityMap(records)" in javascript
    assert "state.map.latLngToLayerPoint" in javascript
    assert "state.teams.length < 6" in javascript
    assert "popupPlayers(team.playerList)" in javascript
    assert ".nfl-team-rosette-icon" in stylesheet
    assert ".selected-team-chips" in stylesheet
    assert 'data-map-sport-switcher' in html
    assert 'id="ranking-toggle"' in html
    assert 'id="ranking-panel"' in html
    assert 'id="ranking-scrim"' in html
    assert "function setRankingOpen(open" in javascript
    assert ".nfl-map-layout.ranking-open .ranking-card" in stylesheet
    assert "grid-template-columns: minmax(0, 1fr) 340px" not in stylesheet


def test_every_explorer_uses_the_shared_map_first_workspace():
    navigation = (ROOT / "docs" / "assets" / "sport-navigation.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "docs" / "assets" / "styles.css").read_text(encoding="utf-8")
    map_pages = [ROOT / "docs" / "index.html"] + [
        ROOT / "docs" / sport / "index.html"
        for sport in ("cricket", "ufc", "formula", "motogp", "volleyball", "athletics", "tennis", "padel", "badminton", "golf", "afl", "nrl", "nba", "nfl", "nhl", "mlb")
    ]

    for page in map_pages:
        html = page.read_text(encoding="utf-8")
        assert 'id="map-explorer"' in html
        assert 'class="map-layout' in html
        assert "assets/sport-navigation.js" in html

    assert "function enhanceMapWorkspace()" in navigation
    assert 'data-map-sport-switcher' in navigation
    assert 'class="ranking-toggle"' in navigation
    assert 'scrim.className = "ranking-scrim"' in navigation
    assert ".map-first-map-layout.ranking-open .ranking-card" in stylesheet
    assert ".map-first-map-layout #talent-map" in stylesheet


def test_shared_team_colour_registry_covers_opted_in_leagues():
    javascript = (ROOT / "docs" / "assets" / "league-app.js").read_text(encoding="utf-8")
    colours = (ROOT / "docs" / "assets" / "team-colours.js").read_text(encoding="utf-8")

    for sport, edition in (("afl", "AFL"), ("nrl", "NRL"), ("nba", "NBA"), ("nhl", "NHL"), ("mlb", "MLB")):
        html = (ROOT / "docs" / sport / "index.html").read_text(encoding="utf-8")
        payload = json.loads((ROOT / "docs" / sport / "data" / "dashboard.json").read_text(encoding="utf-8"))
        assert 'src="../assets/team-colours.js"' in html
        assert f"{edition}: {{" in colours
        for team in payload["meta"]["teams"]:
            assert team in colours

    assert "const TEAM_STYLES" in javascript
    assert "function aggregateTeamPlaces(records)" in javascript
    assert "function renderTeamCityMap(records)" in javascript
    assert "function revealPlaceMarker(marker)" in javascript
    assert "marker.talentPlaceKey = place.key" in javascript
    assert "state.teams.length < 6" in javascript
    assert "projectTeamSplits(row, [split])" in javascript
    assert (ROOT / "docs" / "FEATURE_PARITY.md").exists()
