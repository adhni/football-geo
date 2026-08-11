import pandas as pd

from src.ftg.enrich_top5_wikidata import choose_matches, choose_search_match, sparql_query


def test_sparql_query_and_match_selection():
    players = pd.DataFrame(
        [
            {"player_id": "p1", "player_name": "Player One", "birth_year": 2000},
            {"player_id": "p2", "player_name": "Player Two", "birth_year": 2001},
            {"player_id": "p3", "player_name": "Unknown", "birth_year": pd.NA},
        ]
    )
    query = sparql_query([("Player One", 2000)])
    assert '"Player One"@en 2000' in query
    bindings = [
        {
            "searchName": {"value": "Player One"},
            "birthYear": {"value": "2000"},
            "item": {"value": "http://www.wikidata.org/entity/Q1"},
            "dob": {"value": "2000-02-03T00:00:00Z"},
            "place": {"value": "http://www.wikidata.org/entity/Q10"},
        }
    ]
    matches = choose_matches(players, bindings)
    assert matches["p1"]["resolution_status"] == "resolved"
    assert matches["p1"]["birth_place_qid"] == "Q10"
    assert matches["p2"]["resolution_status"] == "name_birth_year_not_found"
    assert matches["p3"]["resolution_status"] == "birth_year_missing"


def test_search_match_requires_birth_year_and_birthplace():
    results = [
        {"id": "Q1", "description": "English association football player"},
        {"id": "Q2", "description": "American actor"},
    ]
    entities = {
        "Q1": {
            "claims": {
                "P569": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"time": "+2000-02-03T00:00:00Z"}}}}],
                "P19": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q10"}}}}],
            }
        },
        "Q2": {
            "claims": {
                "P569": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"time": "+1990-02-03T00:00:00Z"}}}}],
                "P19": [{"mainsnak": {"snaktype": "value", "datavalue": {"value": {"id": "Q20"}}}}],
            }
        },
    }
    assert choose_search_match(results, entities, 2000)["wikidata_qid"] == "Q1"
    assert choose_search_match(results, entities, 2001) is None
