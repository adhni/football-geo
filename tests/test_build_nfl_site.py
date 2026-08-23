import json

import pandas as pd
import requests

from src.ftg.build_nfl_site import (
    aggregate_snap_cohort,
    build_payload,
    fetch_espn_athletes,
    normalize,
    resolve_birthplace,
)


def test_aggregate_snap_cohort_keeps_regular_season_appearances():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "game_type": "REG", "pfr_player_id": "TestPl00", "player": "Test Player", "position": "LB", "team": "BUF", "offense_snaps": 0, "defense_snaps": 50, "st_snaps": 3},
            {"game_id": "g2", "game_type": "REG", "pfr_player_id": "TestPl00", "player": "Test Player", "position": "LB", "team": "BUF", "offense_snaps": 0, "defense_snaps": 40, "st_snaps": 2},
            {"game_id": "g3", "game_type": "POST", "pfr_player_id": "TestPl00", "player": "Test Player", "position": "LB", "team": "BUF", "offense_snaps": 0, "defense_snaps": 60, "st_snaps": 0},
        ]
    )
    cohort = aggregate_snap_cohort(snaps)
    assert cohort == [{
        "pfr_id": "TestPl00",
        "snap_name": "Test Player",
        "snap_position": "LB",
        "team_code": "BUF",
        "team_codes": ["BUF"],
        "team_splits": [{
            "team_code": "BUF",
            "games": 2,
            "snaps": 95,
            "offense_snaps": 0,
            "defense_snaps": 90,
            "special_teams_snaps": 5,
        }],
        "games": 2,
        "snaps": 95,
        "offense_snaps": 0,
        "defense_snaps": 90,
        "special_teams_snaps": 5,
    }]


def test_resolve_birthplace_requires_correct_us_state():
    assert normalize("São Paulo") == "saopaulo"
    city_index = {
        "springfield": [
            {"name": "Springfield", "lat": 39.8, "lon": -89.6, "country_code": "US", "admin1": "IL", "population": 100000, "geonames_id": "1"},
            {"name": "Springfield", "lat": 44.0, "lon": -123.0, "country_code": "US", "admin1": "OR", "population": 60000, "geonames_id": "2"},
        ]
    }
    result = resolve_birthplace(
        {"birth_city": "Springfield", "birth_state": "OR", "birth_country": "USA"},
        city_index,
        {"usa": "US"},
        {"US": "United States"},
    )
    assert result["lat"] == 44.0
    assert result["country"] == "United States"


def test_resolve_birthplace_rejects_missing_or_unknown_country():
    city_index = {
        "london": [
            {"name": "London", "lat": 51.5, "lon": -0.1, "country_code": "GB", "admin1": "", "population": 9000000, "geonames_id": "1"},
            {"name": "London", "lat": 42.9, "lon": -81.2, "country_code": "CA", "admin1": "08", "population": 400000, "geonames_id": "2"},
        ]
    }

    assert resolve_birthplace({"birth_city": "London"}, city_index, {"canada": "CA"}, {"CA": "Canada"}) is None
    assert resolve_birthplace({"birth_city": "London", "birth_country": "Unknown"}, city_index, {"canada": "CA"}, {"CA": "Canada"}) is None


def test_fetch_espn_athletes_retries_cached_failures(tmp_path, monkeypatch):
    cache_path = tmp_path / "athletes.json"
    cache_path.write_text(json.dumps({"123": {"error": "temporary failure"}}), encoding="utf-8")
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"displayName": "Test Player", "birthPlace": {"city": "Orlando", "country": "USA"}}

    def fake_get(url, **kwargs):
        calls.append(url)
        return Response()

    monkeypatch.setattr("src.ftg.build_nfl_site.requests.get", fake_get)
    athletes = fetch_espn_athletes(["123"], cache_path, workers=1)

    assert len(calls) == 1
    assert athletes["123"]["birth_city"] == "Orlando"
    assert "error" not in json.loads(cache_path.read_text(encoding="utf-8"))["123"]


def test_fetch_espn_athletes_does_not_cache_new_failures(tmp_path, monkeypatch):
    cache_path = tmp_path / "athletes.json"

    def fail(*args, **kwargs):
        raise requests.RequestException("temporary failure")

    monkeypatch.setattr("src.ftg.build_nfl_site.requests.get", fail)
    monkeypatch.setattr("src.ftg.build_nfl_site.time.sleep", lambda *_: None)
    athletes = fetch_espn_athletes(["123"], cache_path, workers=1)

    assert "123" not in athletes
    assert json.loads(cache_path.read_text(encoding="utf-8")) == {}


def test_aggregate_snap_cohort_preserves_team_splits():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "game_type": "REG", "pfr_player_id": "Trade00", "player": "Traded Player", "position": "WR", "team": "BUF", "offense_snaps": 20, "defense_snaps": 0, "st_snaps": 1},
            {"game_id": "g2", "game_type": "REG", "pfr_player_id": "Trade00", "player": "Traded Player", "position": "WR", "team": "ATL", "offense_snaps": 30, "defense_snaps": 0, "st_snaps": 2},
        ]
    )

    cohort = aggregate_snap_cohort(snaps)[0]

    assert cohort["snaps"] == 53
    assert cohort["team_codes"] == ["ATL", "BUF"]
    assert cohort["team_splits"] == [
        {"team_code": "ATL", "games": 1, "snaps": 32, "offense_snaps": 30, "defense_snaps": 0, "special_teams_snaps": 2},
        {"team_code": "BUF", "games": 1, "snaps": 21, "offense_snaps": 20, "defense_snaps": 0, "special_teams_snaps": 1},
    ]


def test_build_nfl_payload_calculates_snap_coverage():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "game_type": "REG", "pfr_player_id": "TestPl00", "player": "Test Player", "position": "LB", "team": "BUF", "offense_snaps": 0, "defense_snaps": 50, "st_snaps": 3},
            {"game_id": "g1", "game_type": "REG", "pfr_player_id": "LostPl00", "player": "Lost Player", "position": "WR", "team": "ATL", "offense_snaps": 20, "defense_snaps": 0, "st_snaps": 0},
        ]
    )
    players = pd.DataFrame(
        [
            {"pfr_id": "TestPl00", "espn_id": 123, "display_name": "Test Player", "position": "LB", "college_name": "Example", "birth_date": "2000-01-01"},
            {"pfr_id": "LostPl00", "espn_id": 456, "display_name": "Lost Player", "position": "WR", "college_name": "Example", "birth_date": "2001-01-01"},
        ]
    )
    athletes = {
        "123": {"birth_city": "Orlando", "birth_state": "FL", "birth_country": "USA", "dob": "2000-01-01"},
        "456": {"birth_city": None},
    }
    cities = {"orlando": [{"name": "Orlando", "lat": 28.54, "lon": -81.38, "country_code": "US", "admin1": "FL", "population": 300000, "geonames_id": "x"}]}
    payload = build_payload(snaps, players, athletes, cities, {"usa": "US"}, {"US": "United States"}, generated_at="2026-08-22T00:00:00+00:00")
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["mapped_snaps"] == 53
    assert payload["records"][1]["place"] == "Orlando"


def test_build_nfl_payload_keeps_season_totals_and_team_contributions():
    snaps = pd.DataFrame(
        [
            {"game_id": "g1", "game_type": "REG", "pfr_player_id": "Trade00", "player": "Traded Player", "position": "WR", "team": "BUF", "offense_snaps": 20, "defense_snaps": 0, "st_snaps": 1},
            {"game_id": "g2", "game_type": "REG", "pfr_player_id": "Trade00", "player": "Traded Player", "position": "WR", "team": "ATL", "offense_snaps": 30, "defense_snaps": 0, "st_snaps": 2},
        ]
    )
    players = pd.DataFrame([{"pfr_id": "Trade00", "espn_id": 123, "display_name": "Traded Player", "position": "WR", "college_name": "Example", "birth_date": "2000-01-01"}])
    athletes = {"123": {"birth_city": "Orlando", "birth_state": "FL", "birth_country": "USA", "dob": "2000-01-01"}}
    cities = {"orlando": [{"name": "Orlando", "lat": 28.54, "lon": -81.38, "country_code": "US", "admin1": "FL", "population": 300000, "geonames_id": "x"}]}

    payload = build_payload(snaps, players, athletes, cities, {"usa": "US"}, {"US": "United States"}, generated_at="2026-08-22T00:00:00+00:00")
    record = payload["records"][0]

    assert payload["summary"]["players"] == 1
    assert payload["summary"]["snaps"] == 53
    assert [(split["teamCode"], split["snaps"]) for split in record["teamSplits"]] == [("ATL", 32), ("BUF", 21)]
