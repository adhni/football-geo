from datetime import date

import pytest

from src.ftg.utils import age_on, normalize_key, write_json


@pytest.mark.parametrize("dob,on_date,expected", [
    ("2000-02-29", date(2025, 2, 28), 24),
    ("2000-02-29", date(2025, 3, 1), 25),
    ("2000-08-24T12:00:00Z", date(2025, 8, 24), 25),
    ("invalid", date(2025, 8, 24), None),
    (None, date(2025, 8, 24), None),
])
def test_age_uses_snapshot_date_and_preserves_unknown_dates(dob, on_date, expected):
    assert age_on(dob, on_date) == expected


def test_builder_date_defaults_and_special_transliteration_are_preserved():
    from src.ftg.build_afl_site import age_on as afl_age
    from src.ftg.build_nfl_site import age_on as nfl_age
    from src.ftg.build_formula_site import normalize as formula_key
    from src.ftg.build_motogp_site import normalize as motogp_key
    from src.ftg.build_volleyball_site import normalize as volleyball_key

    assert afl_age("2000-12-01") == 24
    assert nfl_age("2000-12-01") == 25
    assert normalize_key("São Paulo") == "saopaulo"
    assert normalize_key("Søren") == "sren"
    assert formula_key("Søren") == motogp_key("Søren") == volleyball_key("Søren") == "soren"


def test_failed_json_serialization_preserves_existing_file(tmp_path):
    path = tmp_path / "result.json"
    write_json(path, {"name": "São Paulo"})
    before = path.read_bytes()
    with pytest.raises(TypeError):
        write_json(path, {"invalid": object()})
    assert path.read_bytes() == before
    assert "São Paulo" in path.read_text()
