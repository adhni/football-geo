import csv
import io
import json
from pathlib import Path

import pytest

from src.ftg.build_golf_site import build_payload, parse_owgr_pdf, parse_wwgr_csv, wikipedia_birthplace


ROOT = Path(__file__).resolve().parents[1]


class FakePage:
    def __init__(self, first_rank):
        self.first_rank = first_rank

    def extract_words(self):
        words = []
        for offset in range(50):
            rank = self.first_rank + offset
            top = 100 + offset * 10
            words.extend([
                {"text": str(rank), "x0": 74.0, "top": top},
                {"text": "Player", "x0": 150.0, "top": top},
                {"text": str(rank), "x0": 180.0, "top": top},
                {"text": "United", "x0": 249.0, "top": top},
                {"text": "States", "x0": 270.0, "top": top},
                {"text": "100.000", "x0": 345.0, "top": top},
                {"text": "40", "x0": 388.0, "top": top},
                {"text": "24", "x0": 507.0, "top": top},
            ])
        return words


class FakePdf:
    pages = [FakePage(1), FakePage(51)]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def test_parse_owgr_pdf_requires_and_extracts_exact_top_100(monkeypatch):
    monkeypatch.setattr("src.ftg.build_golf_site.pdfplumber.open", lambda _: FakePdf())
    rows = parse_owgr_pdf(b"fixture")

    assert [row["rank"] for row in rows] == list(range(1, 101))
    assert rows[0]["name"] == "Player 1"
    assert rows[0]["country_code"] == "United States"
    assert rows[0]["total_points"] == 100.0
    assert rows[0]["average_points"] == 2.5
    assert rows[0]["events"] == 24


def wwgr_csv(count=100):
    handle = io.StringIO()
    handle.write("Women's World Golf Rankings - as of 12/29/2025\n")
    writer = csv.DictWriter(handle, fieldnames=[
        "Week", "WwgrId", "Rank", "WeekChange", "YTDChange", "Name", "Country",
        "Events", "TotalPoints", "AveragePoints",
    ])
    writer.writeheader()
    for rank in range(1, count + 1):
        writer.writerow({
            "Week": "12/29/2025", "WwgrId": 7000 + rank, "Rank": rank, "Name": f"Golfer {rank}",
            "Country": "AUS", "Events": 20, "TotalPoints": 101 - rank, "AveragePoints": (101 - rank) / 20,
        })
    return handle.getvalue()


def test_parse_wwgr_csv_uses_stable_ids_and_exact_top_100():
    rows = parse_wwgr_csv(wwgr_csv())
    assert len(rows) == 100
    assert rows[0]["source_player_id"] == "7001"
    assert rows[-1]["rank"] == 100


def test_parse_wwgr_csv_rejects_incomplete_snapshot():
    with pytest.raises(ValueError, match="exact WWGR ranks"):
        parse_wwgr_csv(wwgr_csv(99))


def test_wikipedia_birthplace_accepts_explicit_infobox_location_only():
    html = '<span class="bday">1997-05-07</span><div class="birthplace"><a title="Scarborough, New York">Scarborough</a></div>'
    assert wikipedia_birthplace(html) == ("Scarborough, New York", "1997-05-07")
    assert wikipedia_birthplace('<span class="bday">1997-05-07</span>') == (None, "1997-05-07")


def test_payload_reconciles_points_and_coverage():
    cohort = [
        {"tour": "OWGR", "gender": "Men", "ranking_date": "2025-12-28", "rank": 1, "name": "One", "country_code": "AUS", "total_points": 100.5, "average_points": 2.5, "events": 40, "source_player_id": "one"},
        {"tour": "WWGR", "gender": "Women", "ranking_date": "2025-12-29", "rank": 1, "name": "Two", "country_code": "NZL", "total_points": 80.25, "average_points": 2.0, "events": 40, "source_player_id": "2"},
    ]
    places = {"OWGR:one": {"place": "Melbourne", "country": "Australia", "lat": -37.8, "lon": 145.0}}
    payload = build_payload(cohort, places, {}, generated_at="2025-12-29T00:00:00+00:00")

    assert payload["summary"]["players"] == 2
    assert payload["summary"]["mapped_players"] == 1
    assert payload["summary"]["points"] == 180.75
    assert payload["summary"]["mapped_points"] == 100.5
    assert payload["records"][0]["eventsPlayed"] == 40


def test_published_golf_snapshot_has_two_exact_top_100_rankings():
    payload = json.loads((ROOT / "docs" / "golf" / "data" / "dashboard.json").read_text())
    records = payload["records"]

    assert payload["meta"]["sport"] == "golf"
    assert payload["summary"]["players"] == 200
    assert len({row["id"] for row in records}) == 200
    for tour in ("OWGR", "WWGR"):
        rows = [row for row in records if row["tour"] == tour]
        assert [row["rank"] for row in rows] == list(range(1, 101))
    assert sum(row["points"] for row in records) == pytest.approx(payload["summary"]["points"])
    assert sum(row["points"] for row in records if row["mapped"]) == pytest.approx(payload["summary"]["mapped_points"])
