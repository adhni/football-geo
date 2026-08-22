import pandas as pd

from src.ftg.build_nba_site import build_payload, choose_wikidata_rows, parse_point, wikidata_query


def test_nba_wikidata_helpers_choose_mapped_birthplace():
    assert parse_point("Point(-121.872777777 37.304166666)") == (37.304166666, -121.872777777)
    query = wikidata_query(["203932"])
    assert '"203932"' in query
    assert "wdt:P3647" in query
    bindings = [
        {
            "nbaId": {"value": "203932"},
            "player": {"value": "http://www.wikidata.org/entity/Q1"},
            "playerLabel": {"value": "Player"},
            "birthplace": {"value": "http://www.wikidata.org/entity/Q2"},
            "birthplaceLabel": {"value": "San Jose"},
            "country": {"value": "http://www.wikidata.org/entity/Q30"},
            "countryLabel": {"value": "United States"},
            "coord": {"value": "Point(-121.87 37.30)"},
        }
    ]
    match = choose_wikidata_rows(bindings)["203932"]
    assert match["place"] == "San Jose"
    assert match["lat"] == 37.3


def test_build_nba_payload_calculates_summary_and_player_totals():
    stats = pd.DataFrame(
        {
            "player_id": [203932, 999],
            "player_name": ["Mapped Player", "Unmapped Player"],
            "team": ["DEN", "BOS"],
            "position": ["F", "G"],
            "country": ["USA", "Canada"],
            "age_completed_years": [30, 24],
            "birthdate": ["1995-09-16", "2001-01-01"],
            "minutes_played": [100.4, 50.2],
            "wins": [3, 2],
            "losses": [1, 2],
            "one_point_made": [10, 4],
            "two_point_made": [20, 5],
            "three_point_made": [5, 2],
            "offensive_rebounds": [2, 1],
            "defensive_rebounds": [8, 3],
            "assists": [12, 8],
            "steals": [3, 2],
            "blocks": [1, 0],
        }
    )
    wikidata = {
        "203932": {
            "place": "San Jose",
            "country": "United States",
            "lat": 37.3,
            "lon": -121.87,
            "birth_place_qid": "Q2",
            "wikidata_qid": "Q1",
        }
    }
    payload = build_payload(stats, wikidata, generated_at="2026-08-22T00:00:00+00:00")
    assert payload["meta"]["sport"] == "nba"
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["records"][0]["team"] == "Boston Celtics"
    mapped = next(record for record in payload["records"] if record["mapped"])
    assert mapped["points"] == 65
    assert mapped["games"] == 4
    assert payload["unresolved"] == [{"name": "Unmapped Player", "status": "identity unmatched"}]
