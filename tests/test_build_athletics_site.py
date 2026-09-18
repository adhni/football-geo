from src.ftg import build_athletics_site as athletics


def _competitor(athlete_id, name, dob="01 JAN 2000"):
    return {
        "id": f"internal-{athlete_id}", "name": name, "birthDate": dob,
        "urlSlug": f"country/{name.lower().replace(' ', '-')}-{athlete_id}",
        "teamMembers": None,
    }


def _result(competitor, *, nation="AAA", place="1.", mark="10.00"):
    return {"competitor": competitor, "nationality": nation, "place": place, "mark": mark}


def test_aggregate_results_counts_entries_once_and_excludes_dns(monkeypatch):
    monkeypatch.setattr(athletics, "EXPECTED_EVENT_COUNT", 2)
    runner = _competitor("1001", "Test RUNNER")
    dns = _competitor("1002", "Did Not START")
    relay_runner = {"id": 2001, "name": "Relay RUNNER", "urlSlug": "country/relay-runner-2001"}
    individual = {
        "eventId": 1, "event": "Men's 100 Metres", "gender": "M", "isRelay": False,
        "races": [
            {"race": "Round 1 - Heat", "raceNumber": 1, "results": [_result(runner), _result(dns, mark="DNS", place="")]},
            {"race": "Final", "raceNumber": 1, "results": [_result(runner)]},
        ],
    }
    relay_team = {"id": "team-a", "name": "AAA", "teamMembers": [relay_runner]}
    relay = {
        "eventId": 2, "event": "Men's 4x100 Metres Relay", "gender": "M", "isRelay": True,
        "races": [{"race": "Final", "raceNumber": 1, "results": [_result(relay_team)]}],
    }
    combined_component = {
        "eventId": 1, "event": "Men's 100 Metres", "gender": "M", "isRelay": False,
        "races": [{"race": "Combined - Group", "raceNumber": 1, "results": [_result(runner)]}],
    }
    page = {"eventTitles": [
        {"eventTitle": None, "events": [individual, relay]},
        {"eventTitle": "Combined Events", "events": [combined_component]},
    ]}

    players = athletics.aggregate_results([page])

    assert {row["sourcePlayerId"] for row in players} == {"1001", "2001"}
    by_id = {row["sourcePlayerId"]: row for row in players}
    assert by_id["1001"]["entries"] == 1
    assert by_id["1001"]["eventNames"] == ["Men's 100 Metres"]
    assert by_id["1001"]["rounds"] == 2
    assert by_id["1001"]["gold"] == 1
    assert by_id["2001"]["entries"] == 1
    assert by_id["2001"]["gold"] == 1


def test_published_payload_reconciles_entries_and_birthplace_coverage():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "docs" / "athletics" / "data" / "dashboard.json").read_text())
    records = payload["records"]

    assert len({row["id"] for row in records}) == payload["summary"]["players"]
    assert sum(row["entries"] for row in records) == payload["summary"]["entries"]
    assert sum(row["entries"] for row in records if row["mapped"]) == payload["summary"]["mapped_entries"]
    assert all(row["entries"] == len(row["eventLog"]) for row in records)
    assert all(row["eventNames"] == [event["event"] for event in row["eventLog"]] for row in records)
    assert len({event for row in records for event in row["eventNames"]}) == 49
