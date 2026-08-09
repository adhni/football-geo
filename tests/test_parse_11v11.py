from pathlib import Path

from src.ftg.parse_11v11 import parse_team_season_html
from src.ftg.enrich_players import parse_profile


def test_parse_team_season_html():
    html = (Path(__file__).parent / "fixtures" / "italy_sample.html").read_text()
    rows = parse_team_season_html(html)
    assert len(rows) == 2
    assert rows[0].player_name == "Gianluigi Buffon"
    assert rows[0].starts == 10
    assert rows[0].sub_appearances == 0
    assert rows[1].goals == 1
    assert rows[1].player_url.endswith("/players/mauro-camoranesi-456/")


def test_parse_profile_fields_with_colons():
    html = """
    <dl>
      <dt>Date of birth:</dt><dd>28 January 1978</dd>
      <dt>Place of birth:</dt><dd>Carrara, Italy</dd>
      <dt>Nationality:</dt><dd>Italian</dd>
      <dt>Position:</dt><dd>Goalkeeper</dd>
    </dl>
    """
    profile = parse_profile(html)
    assert profile["dob_source"] == "28 January 1978"
    assert profile["birthplace_text"] == "Carrara, Italy"
