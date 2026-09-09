import json
from pathlib import Path

from src.ftg.build_volleyball_site import (
    EXPECTED_MATCHES,
    aggregate_results,
    normalize,
    parse_match,
    parse_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def scoring_table(player_no, profile_id, name, position, points, attacks, blocks, serves):
    return f"""
    <table class="vbw-stats-scoring vbw-set-all"><tbody><tr data-player-no="{player_no}">
      <td class="playername"><a href="/players/{profile_id}">{name}</a></td>
      <td class="position">{position}</td><td class="total-abs">{points}</td>
      <td class="attacks">{attacks}</td><td class="blocks">{blocks}</td><td class="serves">{serves}</td>
    </tr></tbody></table>
    """


def lineup(side, player_no, first, last):
    return f"""
    <div class="vbw-set-lineup-team-wrapper team-{side}">
      <div class="vbw-set-lineup-player" data-player-id="{player_no}">
        <div class="player-firstname">{first}</div><div class="player-lastname">{last}</div>
      </div>
    </div>
    """


def test_name_normalisation_handles_diacritics():
    assert normalize("Ebrar Karakurt") == "ebrarkarakurt"
    assert normalize("Łukasz Kaczmarek") == "lukaszkaczmarek"


def test_match_parser_counts_only_exact_set_participation():
    stats = (scoring_table("10", "110", "Alpha", "OH", 12, 10, 1, 1) + scoring_table("20", "120", "Beta", "L", 0, 0, 0, 0)).encode()
    court = f"""
      <div class="vbw-sets-lineup-wrapper">
        <div class="vbw-set-lineup-wrapper">{lineup('a', '10', 'Alice', 'Alpha')}{lineup('b', '20', 'Bob', 'Beta')}</div>
        <div class="vbw-set-lineup-wrapper">{lineup('a', '10', 'Alice', 'Alpha')}{lineup('b', '20', 'Bob', 'Beta')}</div>
      </div>
    """.encode()
    match = {"teamANo": 1, "teamBNo": 2, "gender": "Women", "matchNo": 99, "matchNoInTournament": 1, "matchDateUtc": "2025-06-01T00:00:00Z", "roundName": "Pool"}
    teams = {1: {"name": "Team A", "code": "AAA"}, 2: {"name": "Team B", "code": "BBB"}}
    rows = parse_match(stats, court, match, teams)
    assert len(rows) == 2
    assert rows[0]["name"] == "Alice Alpha"
    assert rows[0]["sets"] == 2
    assert rows[0]["points"] == 12


def test_official_profile_parser_reads_dob_position_and_height():
    html = b"""<h1>Alice Alpha</h1><div class='vbw-player-bio-head'>Position</div><div class='vbw-player-bio-text'>Outside hitter</div><div class='vbw-player-bio-head'>Nationality</div><div class='vbw-player-bio-text'>Italy</div><div class='vbw-player-bio-head'>Birth date</div><div class='vbw-player-bio-text'>01/02/2000</div><div class='vbw-player-bio-head'>Height</div><div class='vbw-player-bio-text'>190 cm</div>"""
    profile = parse_profile(html)
    assert profile == {"name": "Alice Alpha", "dob": "2000-02-01", "nationality": "Italy", "position": "Outside hitter", "height": 190}


def test_aggregation_preserves_gender_team_and_match_totals():
    rows = [
        {"gender": "Women", "playerNo": "10", "profileId": "110", "name": "Alice Alpha", "team": "Italy", "teamCode": "ITA", "positionCode": "OH", "matchId": 1, "date": "2025-06-01", "round": "Pool", "opponent": "Brazil", "sets": 3, "matches": 1, "points": 12, "attackPoints": 10, "blockPoints": 1, "servePoints": 1},
        {"gender": "Women", "playerNo": "10", "profileId": "110", "name": "Alice Alpha", "team": "Italy", "teamCode": "ITA", "positionCode": "OH", "matchId": 2, "date": "2025-06-02", "round": "Pool", "opponent": "Japan", "sets": 4, "matches": 1, "points": 8, "attackPoints": 7, "blockPoints": 0, "servePoints": 1},
    ]
    players, profiles = aggregate_results(rows, {"110": {"name": "Alice Alpha", "dob": "2000-02-01", "nationality": "Italy", "position": "Outside hitter", "height": 190}})
    assert len(players) == 1
    assert players[0]["team"] == "Women · Italy"
    assert players[0]["matches"] == 2
    assert players[0]["sets"] == 7
    assert players[0]["points"] == 20
    assert profiles[players[0]["playerId"]]["dob"] == "2000-02-01"


def test_published_volleyball_snapshot_reconciles_exactly():
    payload = json.loads((ROOT / "docs/volleyball/data/dashboard.json").read_text())
    assert payload["meta"]["matches_by_gender"] == EXPECTED_MATCHES
    assert payload["summary"]["matches"] == 232
    assert payload["summary"]["teams"] == 36
    assert payload["summary"]["players"] == 580
    assert payload["summary"]["player_matches"] == 4511
    assert payload["summary"]["sets"] == 14164
    assert len({row["id"] for row in payload["records"]}) == 580
    assert sum(row["matches"] for row in payload["records"]) == payload["summary"]["player_matches"]
    assert sum(row["sets"] for row in payload["records"]) == payload["summary"]["sets"]
    assert all(sum(split["sets"] for split in row["teamSplits"]) == row["sets"] for row in payload["records"])
