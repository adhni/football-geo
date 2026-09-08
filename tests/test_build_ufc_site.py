import json
from pathlib import Path

from src.ftg.build_ufc_site import (
    aggregate_fights,
    build_payload,
    infer_fight_genders,
    merge_details,
    parse_detailed_stats,
    parse_event_results,
)


ROOT = Path(__file__).resolve().parents[1]


def fight_fixture():
    return [{
        "event": "UFC Test", "eventDate": "2025-01-01", "eventUrl": "event", "eventType": "Fight Night",
        "eventLocation": "Las Vegas, United States", "division": "Lightweight", "gender": "Men",
        "fighter1": "One Fighter", "fighter2": "Two Fighter", "fighter1Result": "W", "fighter2Result": "L",
        "fighter1WikiUrl": None, "fighter2WikiUrl": None, "method": "KO (punches)", "round": 1,
        "time": "1:00", "titleBout": False, "notes": "",
    }]


def test_merge_and_aggregation_count_two_appearances_and_finish():
    fights = fight_fixture()
    merge_details(fights, [], {})
    infer_fight_genders(fights)
    players = aggregate_fights(fights, {})
    assert len(players) == 2
    assert sum(row["bouts"] for row in players) == 2
    assert next(row for row in players if row["wins"])["koTkoWins"] == 1


def test_detailed_parser_sums_round_landed_attempted():
    text = 'event_date,player1,player2,player1_url,player2_url,p1_rd1_Sig_str,p2_rd1_Sig_str,p1_rd1_KD,p2_rd1_KD\n"January 01, 2025",One Fighter,Two Fighter,http://ufcstats.com/fighter-details/aaaaaaaaaaaaaaaa,http://ufcstats.com/fighter-details/bbbbbbbbbbbbbbbb,10 of 20,5 of 12,1,0\n'
    row = parse_detailed_stats(text)[0]
    assert row["stats1"]["significantStrikesLanded"] == 10
    assert row["stats1"]["significantStrikesAttempted"] == 20
    assert row["stats1"]["knockdowns"] == 1


def test_published_ufc_snapshot_reconciles_complete_2025_universe():
    payload = json.loads((ROOT / "docs" / "ufc" / "data" / "dashboard.json").read_text())
    records, summary = payload["records"], payload["summary"]
    assert payload["meta"]["sport"] == "ufc"
    assert summary["events"] == 42
    assert summary["fights"] == 520
    assert summary["detailed_fights"] == 515
    assert summary["players"] == 620 == len({row["id"] for row in records})
    assert summary["bouts"] == 1040 == sum(row["bouts"] for row in records)
    assert sum(split["bouts"] for row in records for split in row["teamSplits"]) == 1040
    assert summary["birthplace_mapped_players"] == sum(row["locationType"] == "birthplace" for row in records)
