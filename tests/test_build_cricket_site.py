import io
import json
import zipfile
from pathlib import Path

from src.ftg.build_cricket_site import aggregate_players, build_payload, is_eligible_match, parse_archive


ROOT = Path(__file__).resolve().parents[1]


def match_fixture(*, year="2025", super_over=False):
    return {
        "info": {
            "dates": [f"{year}-01-01"], "gender": "female", "match_type": "T20",
            "team_type": "international", "teams": ["Australia", "Nepal"],
            "players": {"Australia": ["A Batter", "A Bowler"], "Nepal": ["N Batter"]},
            "registry": {"people": {"A Batter": "aaaa1111", "A Bowler": "bbbb2222", "N Batter": "nnnn3333"}},
            "player_of_match": ["A Batter"],
        },
        "innings": [{
            "team": "Australia", "super_over": super_over,
            "overs": [{"over": 0, "deliveries": [
                {"batter": "A Batter", "bowler": "N Batter", "non_striker": "A Bowler", "runs": {"batter": 4, "extras": 0, "total": 4}},
            ]}],
        }, {
            "team": "Nepal", "overs": [{"over": 0, "deliveries": [
                {"batter": "N Batter", "bowler": "A Bowler", "non_striker": "N Batter", "runs": {"batter": 0, "extras": 0, "total": 0}, "wickets": [{"player_out": "N Batter", "kind": "caught", "fielders": [{"name": "A Batter"}]}]},
                {"batter": "N Batter", "bowler": "A Bowler", "non_striker": "N Batter", "runs": {"batter": 0, "extras": 1, "total": 1}, "extras": {"wides": 1}},
            ]}],
        }],
    }


def archive_bytes(matches):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for index, match in enumerate(matches):
            archive.writestr(f"{index}.json", json.dumps(match))
    return buffer.getvalue()


def test_filter_keeps_2025_international_t20_with_full_member_side():
    assert is_eligible_match(match_fixture())
    assert not is_eligible_match(match_fixture(year="2024"))
    domestic = match_fixture()
    domestic["info"]["team_type"] = "domestic"
    assert not is_eligible_match(domestic)


def test_archive_counts_one_appearance_and_delivery_stats_without_associate_players():
    register = {
        "aaaa1111": {"unique_name": "Alice Batter", "key_cricinfo": "1"},
        "bbbb2222": {"unique_name": "Bea Bowler", "key_cricinfo": "2"},
    }
    splits, meta = parse_archive(archive_bytes([match_fixture()]), register)
    players = {row["sourcePlayerId"]: row for row in aggregate_players(splits)}

    assert meta == {"matches": 1, "matches_by_gender": {"Women": 1}, "represented_team_sides": 1}
    assert set(players) == {"aaaa1111", "bbbb2222"}
    assert players["aaaa1111"]["appearances"] == 1
    assert players["aaaa1111"]["runs"] == 4
    assert players["aaaa1111"]["catches"] == 1
    assert players["aaaa1111"]["playerOfMatch"] == 1
    assert players["bbbb2222"]["ballsBowled"] == 1
    assert players["bbbb2222"]["runsConceded"] == 1
    assert players["bbbb2222"]["wickets"] == 1


def test_super_over_deliveries_do_not_enter_performance_totals():
    match = match_fixture(super_over=True)
    splits, _ = parse_archive(archive_bytes([match]), {})
    players = {row["sourcePlayerId"]: row for row in aggregate_players(splits)}
    assert players["aaaa1111"]["appearances"] == 1
    assert players["aaaa1111"]["runs"] == 0


def test_payload_reconciles_mapped_appearance_coverage():
    players = aggregate_players(parse_archive(archive_bytes([match_fixture()]), {})[0])
    payload = build_payload(players, {"aaaa1111": {"place": "Sydney", "country": "Australia", "lat": -33.86, "lon": 151.21}}, {"matches": 1}, generated_at="2026-01-01T00:00:00+00:00")
    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["appearances"] == 2
    assert payload["summary"]["mapped_appearances"] == 1
    assert payload["summary"]["appearance_coverage_pct"] == 50.0


def test_published_cricket_snapshot_reconciles_players_splits_and_appearances():
    payload = json.loads((ROOT / "docs" / "cricket" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    records = payload["records"]
    summary = payload["summary"]
    assert payload["meta"]["sport"] == "cricket"
    assert summary["matches"] == 175
    assert summary["players"] == 446
    assert len({row["id"] for row in records}) == 446
    assert sum(row["appearances"] for row in records) == 3389 == summary["appearances"]
    assert sum(split["appearances"] for row in records for split in row["teamSplits"]) == 3389
    assert sum(row["appearances"] for row in records if row["mapped"]) == summary["mapped_appearances"]
    assert summary["mapped_players"] + summary["unresolved_players"] == 446
