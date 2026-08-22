import pandas as pd

from src.ftg.build_nfl_site import (
    aggregate_snap_cohort,
    build_payload,
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
