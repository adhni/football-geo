from src.ftg.enrich_wikidata import (
    claim_coordinates,
    claim_date,
    claim_entity,
    title_qid_map,
    wikipedia_title,
)


def test_wikipedia_title_and_redirect_qid_mapping():
    assert wikipedia_title("https://en.wikipedia.org/wiki/Gianluigi_Buffon") == "Gianluigi Buffon"
    response = {
        "query": {
            "redirects": [{"from": "Old Name", "to": "Current Name"}],
            "pages": {"1": {"title": "Current Name", "pageprops": {"wikibase_item": "Q1"}}},
        }
    }
    assert title_qid_map(response, ["Old Name"])["Old Name"] == "Q1"


def test_claim_parsers():
    entity = {
        "claims": {
            "P569": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"time": "+1978-01-28T00:00:00Z"}},
                    },
                }
            ],
            "P19": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"id": "Q123"}},
                    },
                }
            ],
            "P625": [
                {
                    "rank": "normal",
                    "mainsnak": {
                        "snaktype": "value",
                        "datavalue": {"value": {"latitude": 44.1, "longitude": 10.1}},
                    },
                }
            ],
        }
    }
    assert claim_date(entity) == "1978-01-28"
    assert claim_entity(entity, "P19") == "Q123"
    assert claim_coordinates(entity) == (44.1, 10.1)
