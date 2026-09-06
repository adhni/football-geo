from src.ftg.build_nrl_site import aggregate_matches, build_payload, parse_fixture, parse_match


def test_fixture_requires_204_complete_matches_and_17_clubs():
    teams = [f"Club {index}" for index in range(17)]
    matches = [{
        "matchId": index + 1, "matchStatus": "complete",
        "homeSquadName": teams[index % 17], "awaySquadName": teams[(index + 1) % 17],
    } for index in range(204)]
    assert len(parse_fixture({"fixture": {"totalMatches": 204, "match": matches}})) == 204


def test_match_parser_uses_aggregate_rows_and_drops_unused_reserves():
    fixture = {
        "matchId": 1, "homeSquadId": 10, "homeSquadName": "Home", "homeSquadCode": "H",
        "awaySquadId": 20, "awaySquadName": "Away", "awaySquadCode": "A",
    }
    payload = {"matchStats": {
        "playerInfo": {"player": [
            {"playerId": 1, "firstname": "A", "surname": "Player"},
            {"playerId": 2, "firstname": "Unused", "surname": "Reserve"},
        ]},
        "playerStats": {"player": [
            {"playerId": 1, "squadId": 10, "position": "Prop", "runMetres": 101, "tackles": 20, "tries": 1, "points": 4},
            {"playerId": 2, "squadId": 10, "position": "Interchange", "runMetres": 0, "tackles": 0, "tries": 0, "points": 0},
        ]},
        "playerPeriodStats": {"player": [{"playerId": 1, "period": 1, "runMetres": 50}]},
    }}
    rows = parse_match(fixture, payload)
    assert len(rows) == 1
    assert rows[0]["run_metres"] == 101


def test_aggregation_preserves_transfer_team_splits():
    rows = [
        {"match_id": "1", "player_id": "1", "name": "Test Player", "team": "A", "team_code": "A", "position": "Prop", "points": 4, "tries": 1, "run_metres": 100, "tackles": 20},
        {"match_id": "2", "player_id": "1", "name": "Test Player", "team": "B", "team_code": "B", "position": "Prop", "points": 0, "tries": 0, "run_metres": 80, "tackles": 30},
    ]
    player = aggregate_matches(rows)[0]
    assert player["games"] == 2
    assert player["run_metres"] == 180
    assert [split["team"] for split in player["team_splits"]] == ["A", "B"]


def test_payload_uses_games_for_geographic_coverage():
    cohort = aggregate_matches([
        {"match_id": "1", "player_id": "1", "name": "Test Player", "team": "A", "team_code": "A", "position": "Prop", "points": 4, "tries": 1, "run_metres": 100, "tackles": 20},
    ])
    payload = build_payload(cohort, {"1": {
        "place": "Sydney", "country": "Australia", "lat": -33.87, "lon": 151.21,
        "dob": "2000-01-01", "wikidata_qid": "Q1", "birth_place_qid": "Q2",
    }}, {"competition_id": 12755, "fixture_retrieved_at": "2026-09-06T00:00:00Z", "matches": 204})
    assert payload["summary"]["mapped_games"] == 1
    assert payload["records"][0]["teamSplits"][0]["runMetres"] == 100
