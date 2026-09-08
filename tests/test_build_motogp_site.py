import json
from pathlib import Path

from src.ftg.build_motogp_site import (
    EXPECTED_RACES,
    aggregate_results,
    birth_city_search_name,
    normalize,
    parse_motogp_classification,
    resolve_official_birth_city,
)


ROOT = Path(__file__).resolve().parents[1]


def result(name, series, team, event, laps, *, source_id="rider-1", position=1, sequence=1):
    return {
        "sourcePlayerId": source_id,
        "name": name,
        "representedCountry": "Australia",
        "series": series,
        "team": team,
        "constructor": "Maker",
        "event": event,
        "eventCode": "AUS",
        "session": "Grand Prix",
        "date": "2025-01-01",
        "sequence": sequence,
        "laps": laps,
        "start": 1,
        "position": position,
        "points": 25.0,
        "win": int(position == 1),
        "podium": int(position <= 3),
        "dnf": 0,
        "status": "INSTND",
        "sourceUrl": "https://example.test/result",
    }


def test_name_normalisation_and_australian_state_birthplace_hint():
    assert normalize("Álex Márquez") == "alexmarquez"
    assert birth_city_search_name("Liverpool NSW") == ("Liverpool", "AU")


def test_motogp_parser_excludes_dns_and_keeps_retired_starters():
    session = {"series": "MotoGP", "event": "Australian GP", "eventCode": "AUS", "session": "Grand Prix", "date": "2025-01-01", "sequence": 1}
    payload = {"classification": [
        {"position": 1, "status": "INSTND", "total_laps": 27, "points": 25, "team_name": "Team A", "rider": {"riders_id": "1", "full_name": "Alex Rider"}},
        {"position": None, "status": "RET", "total_laps": 8, "points": 0, "team_name": "Team B", "rider": {"riders_id": "2", "full_name": "Ben Rider"}},
        {"position": None, "status": "DNS", "total_laps": 0, "points": 0, "team_name": "Team C", "rider": {"riders_id": "3", "full_name": "Chris Rider"}},
    ]}
    rows = parse_motogp_classification(payload, session, "https://example.test")
    assert [row["name"] for row in rows] == ["Alex Rider", "Ben Rider"]
    assert sum(row["laps"] for row in rows) == 35
    assert rows[1]["dnf"] == 1


def test_aggregation_preserves_team_splits_and_cross_series_identity():
    rows = [
        result("Alex Rider", "Moto2", "Team A", "Qatar", 20, sequence=1),
        result("Alex Rider", "Moto2", "Team B", "Italy", 18, position=4, sequence=2),
        result("Alex Rider", "MotoGP", "Team C", "Valencia", 50, sequence=3),
    ]
    player = aggregate_results(rows)[0]
    assert player["series"] == ["MotoGP", "Moto2"]
    assert player["starts"] == 3
    assert player["laps"] == 88
    assert len(player["teamSplits"]) == 3


def test_official_city_resolution_does_not_infer_sporting_nationality():
    profile = {"birth_city": "Rome", "birth_country": "Romania"}
    city_index = {"rome": [{"country_code": "IT", "population": 2_800_000, "lat": 41.9, "lon": 12.5, "geonames_id": "3169070"}]}
    place = resolve_official_birth_city(profile, city_index, {}, {"IT": "Italy", "RO": "Romania"})
    assert place["country"] == "Italy"


def test_published_motogp_snapshot_reconciles_exactly():
    payload = json.loads((ROOT / "docs/motogp/data/dashboard.json").read_text())
    assert payload["meta"]["races_by_series"] == EXPECTED_RACES
    assert payload["summary"]["races"] == 114
    assert payload["summary"]["players"] == 163
    assert payload["summary"]["mapped_players"] == 147
    assert len({row["id"] for row in payload["records"]}) == 163
    assert sum(row["starts"] for row in payload["records"]) == payload["summary"]["starts"]
    assert sum(row["laps"] for row in payload["records"]) == payload["summary"]["laps"]
    assert all(sum(split["starts"] for split in row["teamSplits"]) == row["starts"] for row in payload["records"])
    assert all(sum(split["laps"] for split in row["teamSplits"]) == row["laps"] for row in payload["records"])
