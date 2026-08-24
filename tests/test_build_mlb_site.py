from src.ftg.build_mlb_site import (
    aggregate_team_stats,
    build_payload,
    parse_team_meta,
    profile_summary,
)


def test_parse_mlb_team_meta_requires_and_maps_30_teams():
    payload = {"teams": [{
        "id": index,
        "name": f"Team {index:02d}",
        "abbreviation": f"T{index:02d}",
        "active": True,
        "sport": {"id": 1},
        "league": {"name": "American League" if index < 15 else "National League"},
        "division": {"nameShort": "AL East" if index < 15 else "NL West"},
    } for index in range(1, 31)]}

    teams = parse_team_meta(payload)

    assert len(teams) == 30
    assert teams["1"]["conference"] == "American League"
    assert teams["30"]["code"] == "T30"


def _stat_payload(player_id, name, games, **stats):
    return {"stats": [{"splits": [{
        "stat": {"gamesPlayed": games, **stats},
        "player": {
            "id": player_id,
            "fullName": name,
            "birthCity": "Toronto",
            "birthStateProvince": "Ontario",
            "birthCountry": "CAN",
            "birthDate": "2000-01-02",
            "primaryPosition": {"abbreviation": "P"},
        },
    }]}]}


def test_aggregate_mlb_stats_combines_roles_and_preserves_traded_splits():
    team_meta = {
        "1": {"team": "Alpha", "code": "AAA", "conference": "American League", "division": "AL East"},
        "2": {"team": "Beta", "code": "BBB", "conference": "National League", "division": "NL West"},
    }
    stats = {
        ("1", "hitting"): _stat_payload(7, "Two Way", 10, plateAppearances=40, hits=12, homeRuns=3, rbi=8),
        ("1", "pitching"): _stat_payload(7, "Two Way", 4, battersFaced=25, strikeOuts=9),
        ("2", "hitting"): _stat_payload(7, "Two Way", 5, plateAppearances=18, hits=4, homeRuns=1, rbi=2),
        ("2", "pitching"): {"stats": [{"splits": []}]},
    }

    player = aggregate_team_stats(stats, team_meta)[0]

    assert player["games"] == 15
    assert player["minutes"] == 83
    assert player["hits"] == 16
    assert player["pitching_strikeouts"] == 9
    assert [split["team_code"] for split in player["team_splits"]] == ["AAA", "BBB"]
    assert player["team_splits"][0]["games"] == 10


def test_mlb_profile_summary_keeps_official_birthplace_fields():
    profile = profile_summary({
        "fullName": "Test Player",
        "birthCity": "San Juan",
        "birthStateProvince": "Puerto Rico",
        "birthCountry": "Puerto Rico",
        "birthDate": "1999-04-03",
        "primaryPosition": {"abbreviation": "SS"},
        "batSide": {"code": "S"},
        "pitchHand": {"code": "R"},
    })

    assert profile == {
        "name": "Test Player", "birth_city": "San Juan", "birth_state": "Puerto Rico",
        "birth_country": "Puerto Rico", "dob": "1999-04-03", "position": "SS", "bats": "S", "throws": "R",
    }


def test_build_mlb_payload_reports_workload_and_mapping_coverage():
    team_meta = {
        "1": {"team": "Alpha", "code": "AAA", "conference": "American League", "division": "AL East"},
    }
    cohort = [{
        "player_id": "7", "profile": {
            "name": "Mapped Player", "birth_city": "Toronto", "birth_state": "Ontario",
            "birth_country": "CAN", "dob": "2000-01-02", "position": "CF", "bats": "L", "throws": "R",
        },
        "team_id": "1", "team_ids": ["1"], "games": 12, "minutes": 58,
        "plate_appearances": 50, "batters_faced": 8, "hits": 14, "home_runs": 2, "rbi": 9,
        "pitching_strikeouts": 3,
        "team_splits": [{
            "team_id": "1", "team_code": "AAA", "team": "Alpha", "conference": "American League",
            "division": "AL East", "games": 12, "minutes": 58, "plate_appearances": 50,
            "batters_faced": 8, "hits": 14, "home_runs": 2, "rbi": 9, "pitching_strikeouts": 3,
        }],
    }]
    cities = {"toronto": [{
        "country_code": "CA", "admin1": "08", "population": 3000000,
        "lat": 43.65, "lon": -79.38, "geonames_id": "6167865",
    }]}

    payload = build_payload(
        cohort, cities, {"can": "CA"}, {"CA": "Canada"}, {("CA", "ontario"): "08"}, team_meta,
        generated_at="2026-08-25T00:00:00+00:00",
    )

    record = payload["records"][0]
    assert payload["meta"]["sport"] == "mlb"
    assert payload["meta"]["workload_definition"] == "Plate appearances plus batters faced"
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["minutes"] == 58
    assert record["teamSplits"][0]["plateAppearances"] == 50
    assert record["country"] == "Canada"
    assert record["birthCountry"] == "Canada"
    assert "nationality" not in record


def test_build_mlb_payload_preserves_raw_birthplace_fields_for_qa():
    team_meta = {
        "1": {"team": "Alpha", "code": "AAA", "conference": "American League", "division": "AL East"},
    }
    cohort = [{
        "player_id": "9", "profile": {
            "name": "QA Player", "birth_city": "Small Suburb", "birth_state": "CA",
            "birth_country": "USA", "dob": "2000-01-02", "position": "P", "bats": "R", "throws": "R",
        },
        "team_id": "1", "team_ids": ["1"], "games": 1, "minutes": 3,
        "plate_appearances": 0, "batters_faced": 3, "hits": 0, "home_runs": 0, "rbi": 0,
        "pitching_strikeouts": 1,
        "team_splits": [{
            "team_id": "1", "team_code": "AAA", "team": "Alpha", "conference": "American League",
            "division": "AL East", "games": 1, "minutes": 3, "plate_appearances": 0,
            "batters_faced": 3, "hits": 0, "home_runs": 0, "rbi": 0, "pitching_strikeouts": 1,
        }],
    }]

    payload = build_payload(
        cohort, {}, {"usa": "US"}, {"US": "United States"}, {}, team_meta,
        generated_at="2026-08-25T00:00:00+00:00",
    )

    assert payload["unresolved"] == [{
        "mlbId": "9", "name": "QA Player", "birthCity": "Small Suburb",
        "birthStateProvince": "CA", "birthCountry": "USA",
        "status": "birth city coordinates unavailable",
    }]
