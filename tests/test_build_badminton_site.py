import json
from pathlib import Path

import pytest

from src.ftg.build_badminton_site import (
    EVENTS,
    build_payload,
    claim_entity_ids,
    parse_ranking,
    ranking_url,
    unique_players,
)


ROOT = Path(__file__).resolve().parents[1]


def ranking_markdown(code: str) -> str:
    doubles = not code.endswith("S")
    lines = []
    for rank in range(1, EVENTS[code]["limit"] + 1):
        first_id = 10000 + rank
        countries = f"AAA ![Image {rank}: AAA](flag.png)"
        players = f'[Player {rank}](https://bwfbadminton.com/player/{first_id}/player-{rank} "Player {rank}")'
        if doubles:
            second_id = 20000 + rank
            countries += f" BBB ![Image {rank + 100}: BBB](flag.png)"
            players += f'[Partner {rank}](https://bwfbadminton.com/player/{second_id}/partner-{rank} "Partner {rank}")'
        lines.append(f"| {rank} | {countries} | {players} | 0 | 0 - 0 | N/A | {100_000 - rank:,} / 12 |")
    return "\n".join(lines)


def test_parse_ranking_keeps_exact_singles_and_doubles_cohorts():
    singles = parse_ranking(ranking_markdown("MS"), "MS")
    doubles = parse_ranking(ranking_markdown("MD"), "MD")

    assert len(singles) == 100
    assert len(doubles) == 50
    assert len(singles[0]["players"]) == 1
    assert len(doubles[0]["players"]) == 2
    assert singles[0]["points"] == 99_999
    assert doubles[-1]["rank"] == 50


def test_parse_ranking_rejects_an_incomplete_snapshot():
    with pytest.raises(ValueError, match="Expected exact MS ranks"):
        parse_ranking(ranking_markdown("MS").splitlines()[0], "MS")


def test_build_payload_allocates_pair_points_and_deduplicates_cross_event_athletes():
    shared = {"name": "Shared Player", "player_id": "1", "represented_country": "AAA", "profile_url": "https://example/1"}
    partner = {"name": "Partner", "player_id": "2", "represented_country": "BBB", "profile_url": "https://example/2"}
    rankings = [
        {"event": "MS", "event_name": "Men's Singles", "conference": "Men", "rank": 8, "points": 8_000, "tournaments": 10, "players": [shared]},
        {"event": "MD", "event_name": "Men's Doubles", "conference": "Men", "rank": 4, "points": 12_000, "tournaments": 11, "players": [shared, partner]},
    ]
    places = {
        "1": {"place": "Alpha", "country": "Example", "lat": 1.0, "lon": 2.0, "dob": "2000-01-01"},
    }

    payload = build_payload(rankings, places, {}, generated_at="2025-12-30T00:00:00+00:00")
    records = {record["sourcePlayerId"]: record for record in payload["records"]}

    assert payload["summary"]["players"] == 2
    assert payload["summary"]["ranked_entries"] == 3
    assert payload["summary"]["pairs"] == 1
    assert records["1"]["points"] == 14_000
    assert records["2"]["points"] == 6_000
    assert records["1"]["rank"] == 4
    assert len(records["1"]["teamSplits"]) == 2
    assert sum(record["points"] for record in records.values()) == 20_000
    assert payload["summary"]["mapped_points"] == 14_000


def test_unique_players_uses_stable_bwf_id_and_rejects_conflicting_names():
    rankings = [{"players": [{"player_id": "7", "name": "Same Name"}, {"player_id": "7", "name": "Same Name"}]}]
    assert unique_players(rankings) == [{"player_id": "7", "name": "Same Name"}]

    rankings[0]["players"][1]["name"] = "Different Name"
    with pytest.raises(ValueError, match="inconsistent names"):
        unique_players(rankings)


def test_archive_url_uses_2026_week_one_for_30_december_2025_snapshot():
    assert ranking_url("WS").endswith("/2026/1/?page_no=1&rows=100")


def test_claim_entity_ids_reads_all_entity_type_claims():
    entity = {"claims": {"P31": [
        {"mainsnak": {"datavalue": {"value": {"id": "Q6256"}}}},
        {"mainsnak": {"datavalue": {"value": {"id": "Q3624078"}}}},
    ]}}
    assert claim_entity_ids(entity, "P31") == {"Q6256", "Q3624078"}


def test_published_badminton_snapshot_reconciles_ranked_units_athletes_and_points():
    payload = json.loads((ROOT / "docs" / "badminton" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    summary = payload["summary"]
    records = payload["records"]

    assert payload["meta"]["sport"] == "badminton"
    assert summary["events"] == 5
    assert summary["pairs"] == 150
    assert summary["ranked_entries"] == 500
    assert summary["players"] == 468
    assert len({record["id"] for record in records}) == 468
    assert sum(len(record["teamSplits"]) for record in records) == 500
    assert sum(record["points"] for record in records) == summary["points"]
    assert sum(record["points"] for record in records if record["mapped"]) == summary["mapped_points"]
    assert summary["mapped_players"] + summary["unresolved_players"] == summary["players"]
