import copy
import json
from pathlib import Path

import pytest

from src.ftg.build_edition_catalog import build_catalog, render_script, validate_dashboard, run as check_editions
from src.ftg.build_language_catalog import build_catalog as build_languages, run as check_languages

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_reconciles_all_published_snapshots_and_separates_sports_from_editions():
    config = json.loads((ROOT / "config/editions.json").read_text())
    catalog = build_catalog(config, ROOT / "docs")
    editions = {entry["id"]: entry for entry in catalog}
    assert len(catalog) == 17
    assert editions["nba"]["sportId"] == "basketball"
    assert editions["nfl"]["sportId"] == "american-football"
    assert editions["afl"]["coverage"] == 34.2
    assert editions["afl"]["mappedCoverage"] == 47.4
    assert editions["ufc"]["coverage"] == 49.4
    assert editions["ufc"]["mappedCoverage"] == 84.2
    assert editions["football"]["participants"] == 2690
    assert (ROOT / "docs/assets/edition-catalog.js").read_text() == render_script(catalog)
    check_editions(check=True)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), 91, "51.5"])
def test_dashboard_validation_rejects_invalid_mapped_coordinates(invalid):
    payload = json.loads((ROOT / "docs/tennis/data/dashboard.json").read_text())
    payload["records"][0]["lat"] = invalid
    with pytest.raises(ValueError, match="coordinates"):
        validate_dashboard(payload, {"id": "tennis", "workloadField": "points"})


def test_dashboard_validation_deduplicates_people_but_preserves_workload_contributions():
    payload = {"records": [
        {"id": "a", "name": "Player", "team": "A", "year": 2026, "mapped": False, "starts": 20},
        {"id": "a", "name": "Player", "team": "B", "year": 2026, "mapped": False, "starts": 17},
    ], "summary": {"players": 1, "mapped_players": 0, "unresolved_players": 1, "starts": 37}}
    validate_dashboard(payload, {"id": "football", "workloadField": "starts"})
    broken = copy.deepcopy(payload)
    broken["summary"]["starts"] = 20
    with pytest.raises(ValueError, match="Workload"):
        validate_dashboard(broken, {"id": "football", "workloadField": "starts"})


def test_language_catalogs_preserve_complete_existing_languages_and_label_previews():
    catalog = build_languages(ROOT / "config/locales")
    assert set(catalog) == {"en", "es", "fr", "ar", "id", "pt", "de", "it"}
    assert catalog["ar"]["dir"] == "rtl"
    for code in ("es", "fr", "ar", "id"):
        assert catalog[code]["messages"].keys() == catalog["en"]["messages"].keys()
    for code in ("pt", "de", "it"):
        assert catalog[code]["status"] == "preview"
        assert catalog[code]["translatedMessages"] >= 200
    check_languages(check=True)


def test_language_validation_rejects_mismatched_interpolation_parameters(tmp_path):
    (tmp_path / "index.json").write_text(json.dumps({"en": {"name": "English", "locale": "en-US", "dir": "ltr"}, "es": {"name": "Español", "locale": "es-ES", "dir": "ltr"}}))
    (tmp_path / "en.json").write_text(json.dumps({"label": "Hello {name}"}))
    (tmp_path / "es.json").write_text(json.dumps({"label": "Hola {wrong}"}))
    with pytest.raises(ValueError, match="parameters"):
        build_languages(tmp_path)
