from src.ftg.build_formula_site import (
    EXPECTED_RACES,
    aggregate_results,
    build_payload,
    discover_archive_links,
    match_driver,
    normalize,
    parse_f1_json,
    parse_fia_classification_html,
)


def roster(name, series, points=0, country="Australia"):
    return {
        "name": name,
        "series": series,
        "points": points,
        "rank": 1,
        "representedCountry": country,
        "wikipediaTitle": name,
        "wikipediaUrl": f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
    }


def result(name, series, team, event, laps, *, position=1, sequence=1):
    return {
        "name": name,
        "series": series,
        "team": team,
        "event": event,
        "session": "Feature Race",
        "sequence": sequence,
        "laps": laps,
        "start": 1,
        "position": position,
        "points": 0,
        "win": int(position == 1),
        "podium": int(position <= 3),
        "dnf": 0,
        "status": str(position),
        "sourceUrl": "https://example.test/result",
    }


def test_name_normalisation_and_initial_matching_handle_driver_variants():
    rows = [roster("Søren Müller", "Formula 3"), roster("Alex Dunne", "Formula 3")]
    assert normalize("Søren Müller") == "sorenmuller"
    assert match_driver("S. MULLER", rows)["name"] == "Søren Müller"
    assert match_driver("A. Dunne", rows)["name"] == "Alex Dunne"


def test_archive_discovery_keeps_2025_races_and_deduplicates_links():
    html = """
      <a href="/events/formula-3/season-2025/bahrain/feature-race-classification">Feature Race Classification</a>
      <a href="/events/formula-3/season-2025/bahrain/feature-race-classification?copy=1">Feature Race Classification</a>
      <a href="/events/formula-3/season-2024/monza/sprint-race-classification">Sprint Race Classification</a>
    """
    rows = discover_archive_links(html, "https://www.fia.com/formula-3-championship-archives", "Formula 3")
    assert [(row["event"], row["session"]) for row in rows] == [("Bahrain", "Feature Race")]


def test_fia_parser_excludes_dns_but_keeps_retired_starter():
    rows = [roster("Alex Driver", "Formula 3"), roster("Ben Racer", "Formula 3")]
    html = """
      <table><tr><th>Pos</th><th>Driver</th><th>Team</th><th>Laps</th><th>Points</th></tr>
      <tr><td>1</td><td>A. Driver AUS</td><td>Team One</td><td>22</td><td>10</td></tr>
      <tr><td>DNF</td><td>B. Racer GBR</td><td>Team Two</td><td>5</td><td>0</td></tr></table>
    """
    parsed = parse_fia_classification_html(html, series="Formula 3", event="Bahrain", session="Feature Race", url="x", roster=rows, sequence=1)
    assert sum(row["start"] for row in parsed) == 2
    assert sum(row["laps"] for row in parsed) == 27
    assert parsed[1]["dnf"] == 1


def test_f1_json_parses_grand_prix_and_retirement_laps():
    rows = [roster("Alex Driver", "Formula 1")]
    payload = {"MRData": {"RaceTable": {"Races": [{"round": "1", "raceName": "Australian Grand Prix", "Results": [{"position": "18", "positionText": "R", "points": "0", "laps": "12", "status": "Engine", "Driver": {"givenName": "Alex", "familyName": "Driver"}, "Constructor": {"name": "Team One"}}]}]}}}
    parsed = parse_f1_json(payload, rows, sprint=False)
    assert parsed[0]["session"] == "Grand Prix"
    assert parsed[0]["start"] == 1
    assert parsed[0]["laps"] == 12
    assert parsed[0]["dnf"] == 1


def test_aggregation_preserves_team_splits_and_cross_series_identity():
    rosters = {
        "Formula 1": [roster("Alex Driver", "Formula 1", 25)],
        "Formula 2": [roster("Alex Driver", "Formula 2", 10)],
        "Formula 3": [],
        "F1 Academy": [],
    }
    results = [
        result("Alex Driver", "Formula 2", "Team A", "Bahrain", 20, sequence=1),
        result("Alex Driver", "Formula 2", "Team B", "Monza", 18, position=4, sequence=2),
        result("Alex Driver", "Formula 1", "Team C", "Abu Dhabi", 50, sequence=3),
    ]
    players = aggregate_results(results, rosters)
    assert len(players) == 1
    assert len(players[0]["teamSplits"]) == 3
    assert players[0]["series"] == ["Formula 1", "Formula 2"]
    assert players[0]["starts"] == 3
    assert players[0]["laps"] == 88
    assert players[0]["points"] == 35


def test_payload_coverage_and_published_snapshot_reconcile():
    rosters = {series: [] for series in EXPECTED_RACES}
    rosters["Formula 1"] = [roster("Alex Driver", "Formula 1", 25), roster("Ben Racer", "Formula 1", 0)]
    players = aggregate_results([
        result("Alex Driver", "Formula 1", "Team A", "Australia", 50),
        result("Ben Racer", "Formula 1", "Team B", "Australia", 25, position=4),
    ], rosters)
    places = {"alexdriver": {"dob": "2000-01-01", "place": "Melbourne", "country": "Australia", "lat": -37.8, "lon": 145.0}}
    payload = build_payload(players, places, {"races_by_series": {"Formula 1": 1, "Formula 2": 0, "Formula 3": 0, "F1 Academy": 0}}, generated_at="2026-01-01T00:00:00+00:00")
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["player_coverage_pct"] == 50.0
    assert payload["summary"]["lap_coverage_pct"] == 66.7
    assert payload["summary"]["starts"] == 2


def test_published_formula_snapshot_has_exact_series_race_and_driver_totals():
    import json
    from pathlib import Path

    payload = json.loads((Path(__file__).resolve().parents[1] / "docs/formula/data/dashboard.json").read_text())
    assert payload["meta"]["races_by_series"] == EXPECTED_RACES
    assert payload["summary"]["races"] == 90
    assert payload["summary"]["players"] == 106
    assert len({row["id"] for row in payload["records"]}) == 106
    assert sum(row["starts"] for row in payload["records"]) == payload["summary"]["starts"]
    assert sum(row["laps"] for row in payload["records"]) == payload["summary"]["laps"]
    assert all(sum(split["starts"] for split in row["teamSplits"]) == row["starts"] for row in payload["records"])
    assert all(sum(split["laps"] for split in row["teamSplits"]) == row["laps"] for row in payload["records"])
