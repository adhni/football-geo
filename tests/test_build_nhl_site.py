from src.ftg.build_nhl_site import (
    aggregate_club_stats,
    build_payload,
    parse_team_meta,
    profile_summary,
    resolve_birthplace,
)


def test_parse_nhl_team_meta_requires_and_maps_32_teams():
    standings = {
        "standings": [
            {
                "teamAbbrev": {"default": f"T{index:02d}"},
                "teamName": {"default": f"Team {index:02d}"},
                "conferenceName": "Eastern" if index < 16 else "Western",
                "divisionName": "Atlantic" if index < 8 else "Central",
            }
            for index in range(32)
        ]
    }

    teams = parse_team_meta(standings)

    assert len(teams) == 32
    assert teams["T00"]["conference"] == "Eastern Conference"
    assert teams["T31"]["team"] == "Team 31"


def test_aggregate_nhl_club_stats_preserves_traded_player_splits_and_goalies():
    team_meta = {
        "AAA": {"team": "Alpha", "conference": "Eastern Conference", "division": "Atlantic Division"},
        "BBB": {"team": "Beta", "conference": "Western Conference", "division": "Central Division"},
    }
    clubs = {
        "AAA": {
            "skaters": [{
                "playerId": 1, "firstName": {"default": "Trade"}, "lastName": {"default": "Player"},
                "positionCode": "C", "gamesPlayed": 10, "avgTimeOnIcePerGame": 600,
                "goals": 2, "assists": 3, "points": 5,
            }],
            "goalies": [{
                "playerId": 2, "firstName": {"default": "Goalie"}, "lastName": {"default": "One"},
                "gamesPlayed": 2, "timeOnIce": 7200, "goals": 0, "assists": 1, "points": 1,
            }],
        },
        "BBB": {
            "skaters": [{
                "playerId": 1, "firstName": {"default": "Trade"}, "lastName": {"default": "Player"},
                "positionCode": "C", "gamesPlayed": 5, "avgTimeOnIcePerGame": 720,
                "goals": 1, "assists": 2, "points": 3,
            }],
            "goalies": [],
        },
    }

    cohort = aggregate_club_stats(clubs, team_meta)
    traded = next(player for player in cohort if player["player_id"] == "1")
    goalie = next(player for player in cohort if player["player_id"] == "2")

    assert traded["games"] == 15
    assert traded["minutes"] == 160
    assert traded["points"] == 8
    assert [split["team_code"] for split in traded["team_splits"]] == ["AAA", "BBB"]
    assert goalie["position"] == "G"
    assert goalie["minutes"] == 120


def test_nhl_profile_and_birthplace_resolution_honor_country_and_province():
    profile = profile_summary({
        "firstName": {"default": "Test"},
        "lastName": {"default": "Skater"},
        "birthCity": {"default": "Springfield"},
        "birthStateProvince": {"default": "Ontario"},
        "birthCountry": "CAN",
        "birthDate": "2000-01-02",
    })
    city_index = {
        "springfield": [
            {"country_code": "US", "admin1": "IL", "population": 100000, "lat": 39.8, "lon": -89.6, "geonames_id": "1"},
            {"country_code": "CA", "admin1": "08", "population": 1000, "lat": 43.0, "lon": -80.0, "geonames_id": "2"},
        ]
    }

    birthplace = resolve_birthplace(
        profile,
        city_index,
        {"can": "CA"},
        {"CA": "Canada"},
        {("CA", "ontario"): "08"},
    )

    assert birthplace == {
        "place": "Springfield", "country": "Canada", "lat": 43.0, "lon": -80.0, "geonames_id": "2"
    }


def test_build_nhl_payload_reports_scope_and_mapping_coverage():
    team_meta = {
        "AAA": {"team": "Alpha", "conference": "Eastern Conference", "division": "Atlantic Division"},
    }
    cohort = [{
        "player_id": "1", "name": "Mapped Player", "position": "D", "team_code": "AAA",
        "team_codes": ["AAA"], "games": 12, "minutes": 240, "goals": 3, "assists": 7, "points": 10,
        "team_splits": [{
            "team_code": "AAA", "team": "Alpha", "conference": "Eastern Conference",
            "division": "Atlantic Division", "games": 12, "minutes": 240, "goals": 3, "assists": 7, "points": 10,
        }],
    }]
    profiles = {"1": {
        "name": "Mapped Player", "birth_city": "Toronto", "birth_state": "Ontario",
        "birth_country": "CAN", "dob": "2000-01-02", "shoots_catches": "L",
    }}
    cities = {"toronto": [{
        "country_code": "CA", "admin1": "08", "population": 3000000,
        "lat": 43.65, "lon": -79.38, "geonames_id": "6167865",
    }]}

    payload = build_payload(
        cohort, profiles, cities, {"can": "CA"}, {"CA": "Canada"},
        {("CA", "ontario"): "08"}, team_meta, generated_at="2026-08-25T00:00:00+00:00",
    )

    record = payload["records"][0]
    assert payload["meta"]["sport"] == "nhl"
    assert payload["summary"]["players"] == 1
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["minutes"] == 240
    assert record["teamSplits"][0]["minutes"] == 240
    assert record["country"] == "Canada"
    assert record["rebounds"] == record["goals"] == 3
