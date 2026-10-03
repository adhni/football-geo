import csv
import io

import pytest

from src.ftg.build_tennis_site import build_payload, parse_cohort, run


def _csv(fieldnames, rows):
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def _cohort_inputs(tour="ATP", count=100):
    date = "20251117" if tour == "ATP" else "20251110"
    rankings = _csv(
        ["ranking_date", "rank", "player", "points", "tours"],
        [{"ranking_date": date, "rank": rank, "player": 1000 + rank, "points": 10001 - rank, "tours": 20} for rank in range(1, count + 1)],
    )
    players = _csv(
        ["player_id", "name_first", "name_last", "hand", "dob", "ioc", "height", "wikidata_id"],
        [{"player_id": 1000 + rank, "name_first": "Player", "name_last": str(rank), "hand": "R", "dob": "20000101", "ioc": "AUS", "height": "180", "wikidata_id": f"Q{rank}"} for rank in range(1, count + 1)],
    )
    return rankings, players


@pytest.mark.parametrize("tour", ["ATP", "WTA"])
def test_parse_cohort_requires_exact_year_end_top_100(tour):
    rankings, players = _cohort_inputs(tour)
    cohort = parse_cohort(rankings, players, tour)

    assert len(cohort) == 100
    assert [row["rank"] for row in cohort] == list(range(1, 101))
    assert cohort[0]["points"] == 10000
    assert cohort[0]["dob"] == "2000-01-01"


def test_parse_cohort_rejects_incomplete_ranking():
    rankings, players = _cohort_inputs("ATP", 99)
    with pytest.raises(ValueError, match="ranks 1–100"):
        parse_cohort(rankings, players, "ATP")


def test_payload_reconciles_players_and_point_coverage():
    rankings, players = _cohort_inputs("ATP")
    cohort = parse_cohort(rankings, players, "ATP")[:2]
    places = {"ATP:1001": {
        "place": "Melbourne", "country": "Australia", "lat": -37.81, "lon": 144.96,
        "dob": "2000-01-01", "wikidata_qid": "Q1", "birth_place_qid": "Q2",
    }}
    payload = build_payload(cohort, places, {}, generated_at="2026-09-06T00:00:00+00:00")

    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["points"] == 19999
    assert payload["summary"]["mapped_points"] == 10000
    assert payload["records"][0]["rank"] == 1
    assert payload["records"][0]["locationType"] == "birthplace"


def test_top_250_and_explicit_historical_dates_keep_their_actual_scope_and_age():
    rankings, players = _cohort_inputs("ATP", 250)
    rankings = rankings.replace("20251117", "20241118")
    cohort = parse_cohort(rankings, players, "ATP", ranking_date="20241118", limit=250)
    payload = build_payload(cohort, {}, {}, limit=250, ranking_dates={"ATP": "20241118", "WTA": "20241111"})
    assert len(cohort) == 250
    assert payload["meta"]["year"] == 2024
    assert payload["meta"]["cohort_limit"] == 250
    assert payload["meta"]["season"] == "2024 ranking snapshot"
    assert "year-end" not in payload["meta"]["scope"]
    assert payload["records"][0]["age"] == 24
    assert payload["records"][0]["year"] == 2024
    assert "2025" not in str(payload["meta"]["ranking_source_urls"])


def test_custom_tennis_cohort_cannot_overwrite_the_published_snapshot():
    with pytest.raises(ValueError, match="require --output"):
        run(limit=250)
    with pytest.raises(ValueError, match="one year"):
        run(ranking_dates={"ATP": "20241118", "WTA": "20251110"})
