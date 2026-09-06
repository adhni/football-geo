import pandas as pd

from src.ftg.build_afl_site import (
    aggregate_afl_stats,
    build_payload,
    choose_wikidata_rows,
    filter_home_and_away,
    wikipedia_birthplace,
    wikipedia_club_location_titles,
    wikipedia_football_origin,
)


def sample_stats():
    rows = []
    for team in [
        "Adelaide", "Brisbane Lions", "Carlton", "Collingwood", "Essendon", "Footscray",
        "Fremantle", "Geelong", "Gold Coast", "GWS", "Hawthorn", "Melbourne",
        "North Melbourne", "Port Adelaide", "Richmond", "St Kilda", "Sydney", "West Coast",
    ]:
        rows.append({
            "Season": 2025, "Round": "1", "Date": "2025-03-01", "ID": len(rows) + 1,
            "Player": f"Player {len(rows) + 1}", "Team": team, "DOB": "1-Jan-2000",
            "Disposals": 10, "Goals": 1, "Marks": 2, "Tackles": 3, "url": "https://example.test/player",
        })
    rows.append({**rows[0], "Round": "QF", "Disposals": 99})
    return pd.DataFrame(rows)


def test_filter_home_and_away_excludes_finals_and_validates_clubs():
    rows = filter_home_and_away(sample_stats())
    assert len(rows) == 18
    assert "QF" not in set(rows["Round"].astype(str))


def test_aggregate_afl_stats_preserves_team_splits():
    stats = sample_stats()
    traded = {**stats.iloc[0].to_dict(), "Round": "2", "Date": "2025-03-08", "Team": "Carlton", "Disposals": 20}
    stats = pd.concat([stats, pd.DataFrame([traded])], ignore_index=True)
    player = next(row for row in aggregate_afl_stats(stats) if row["player_id"] == "1")
    assert player["games"] == 2
    assert player["disposals"] == 30
    assert [split["team"] for split in player["team_splits"]] == ["Adelaide Crows", "Carlton"]


def test_choose_wikidata_rows_requires_one_coordinate_match():
    bindings = [{
        "sourceId": {"value": "1"}, "item": {"value": "http://www.wikidata.org/entity/Q1"},
        "place": {"value": "http://www.wikidata.org/entity/Q2"}, "placeLabel": {"value": "Melbourne"},
        "coord": {"value": "Point(144.9631 -37.8136)"}, "countryLabel": {"value": "Australia"},
    }]
    assert choose_wikidata_rows(bindings)["1"]["lat"] == -37.8136


def test_build_afl_payload_uses_games_for_coverage():
    cohort = aggregate_afl_stats(sample_stats())[:1]
    payload = build_payload(cohort, {"1": {
        "place": "Adelaide", "country": "Australia", "lat": -34.93, "lon": 138.6,
        "wikidata_qid": "Q1", "birth_place_qid": "Q2",
    }}, generated_at="2026-09-06T00:00:00+00:00")
    assert payload["meta"]["sport"] == "afl"
    assert payload["summary"]["games"] == 1
    assert payload["summary"]["mapped_games"] == 1
    assert payload["summary"]["birthplace_mapped_players"] == 1
    assert payload["records"][0]["teamSplits"][0]["games"] == 1


def test_player_ids_and_every_stat_reconcile_to_team_splits():
    cohort = aggregate_afl_stats(sample_stats())
    assert len({player["player_id"] for player in cohort}) == len(cohort)
    for player in cohort:
        for field in ("games", "disposals", "goals", "marks", "tackles"):
            assert player[field] == sum(split[field] for split in player["team_splits"])


def test_wikipedia_birthplace_reads_only_explicit_infobox_field():
    text = """{{Infobox AFL biography
| name = Test Player
| birth_date = {{Birth date and age|2000|1|2}}
| birth_place = [[Mount Duneed, Victoria|Mount Duneed]], [[Victoria (state)|Victoria]], Australia
| originalteam = Geelong Falcons
}}"""
    assert wikipedia_birthplace(text) == ("Mount Duneed, Victoria, Australia", "Mount Duneed, Victoria")
    assert wikipedia_birthplace("Born and raised in Melbourne") == (None, None)


def test_wikipedia_football_origin_is_distinct_from_birthplace():
    text = """{{Infobox AFL biography
| birth_place = [[Melbourne]], Australia
| originalteam = [[Sandringham Dragons]] ([[Talent League]])/[[Beaumaris Football Club|Beaumaris]]
}}"""
    assert wikipedia_football_origin(text) == (
        "Sandringham Dragons (Talent League)/Beaumaris",
        "Sandringham Dragons",
    )
    assert wikipedia_football_origin("Born and raised in Melbourne") == (None, None)


def test_wikipedia_club_location_titles_reads_explicit_ground_fields():
    text = """{{Infobox Australian football club
| ground = [[Highgate Recreation Reserve]], [[Craigieburn, Victoria|Craigieburn]]
| league = [[Talent League]]
}}"""
    assert wikipedia_club_location_titles(text) == ["Highgate Recreation Reserve", "Craigieburn, Victoria"]


def test_payload_labels_football_origin_fallback_without_calling_it_birthplace():
    cohort = aggregate_afl_stats(sample_stats())[:1]
    payload = build_payload(cohort, {"1": {
        "place": "Sandringham Dragons", "country": "Australia", "lat": -37.95, "lon": 145.0,
        "location_type": "football_origin", "origin_qid": "Q1", "origin_label": "Sandringham Dragons",
        "origin_precision": "home venue", "resolution_source": "English Wikipedia original-team field + Wikidata",
    }})
    record = payload["records"][0]
    assert record["mapped"] is True
    assert record["birthplaceMapped"] is False
    assert record["locationType"] == "football_origin"
    assert record["birthplaceSource"] is None
    assert payload["summary"]["origin_fallback_players"] == 1
    assert payload["summary"]["birthplace_mapped_players"] == 0
