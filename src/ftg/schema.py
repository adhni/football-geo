from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

MIN_SEASON_END_YEAR = 2000
MAX_SEASON_END_YEAR = 2026

CANONICAL_COLUMNS = [
    "team",
    "fifa_code",
    "season",
    "season_end_year",
    "player_id",
    "player_name",
    "player_url",
    "starts",
    "sub_appearances",
    "goals",
    "position_source",
    "source_url",
    "retrieved_at",
]

REQUIRED_COLUMNS = [
    "team",
    "fifa_code",
    "season",
    "season_end_year",
    "player_id",
    "player_name",
    "starts",
    "sub_appearances",
]

COLUMN_ALIASES = {
    "country": "team",
    "squad": "team",
    "code": "fifa_code",
    "player": "player_name",
    "name": "player_name",
    "a": "starts",
    "s": "sub_appearances",
    "subs": "sub_appearances",
    "substitutions": "sub_appearances",
    "g": "goals",
    "position": "position_source",
    "profile_url": "player_url",
}

ISSUE_COLUMNS = ["severity", "code", "row_number", "column", "value", "message"]


@dataclass(frozen=True)
class ValidationResult:
    data: pd.DataFrame
    issues: pd.DataFrame

    @property
    def has_errors(self) -> bool:
        return bool((self.issues["severity"] == "error").any()) if not self.issues.empty else False


def season_label(end_year: int) -> str:
    return f"{end_year - 1}-{end_year % 100:02d}"


def parse_season_end_year(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}", text):
        return int(text)
    match = re.fullmatch(r"(\d{4})\s*[-/]\s*(\d{2}|\d{4})", text)
    if not match:
        return None
    start = int(match.group(1))
    raw_end = match.group(2)
    if len(raw_end) == 4:
        return int(raw_end)
    end = (start // 100) * 100 + int(raw_end)
    return end + 100 if end <= start else end


def stable_player_id(player_name: Any, player_url: Any = None, dob: Any = None) -> str | None:
    name = "" if player_name is None or pd.isna(player_name) else str(player_name).strip()
    if not name:
        return None
    url = "" if player_url is None or pd.isna(player_url) else str(player_url).strip()
    birth = "" if dob is None or pd.isna(dob) else str(dob).strip()
    key = url or f"{name.casefold()}|{birth}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _issue(
    issues: list[dict[str, Any]],
    severity: str,
    code: str,
    row_number: int | None,
    column: str | None,
    value: Any,
    message: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "code": code,
            "row_number": row_number,
            "column": column,
            "value": None if value is None or pd.isna(value) else str(value),
            "message": message,
        }
    )


def normalize_player_seasons(frame: pd.DataFrame, cohort: pd.DataFrame) -> ValidationResult:
    """Normalize an incoming player-season table and report every validation issue.

    Aliased source columns are retained. Canonical columns are copied from them only
    when the canonical name is absent, preserving the original source fields.
    """
    data = frame.copy()
    issues: list[dict[str, Any]] = []

    stripped = [str(column).strip() for column in data.columns]
    if len(set(stripped)) != len(stripped):
        raise ValueError("Column names are duplicated after trimming whitespace")
    data.columns = stripped
    data.insert(0, "_input_row", range(2, len(data) + 2))

    lower_names = {column.casefold(): column for column in data.columns}
    for alias, canonical in COLUMN_ALIASES.items():
        source = lower_names.get(alias)
        if source is None:
            continue
        if canonical not in data.columns:
            data[canonical] = data[source]
        else:
            missing = data[canonical].isna()
            if pd.api.types.is_string_dtype(data[canonical]):
                missing |= data[canonical].astype("string").str.strip().eq("")
            data.loc[missing, canonical] = data.loc[missing, source]

    team_to_code = dict(zip(cohort["team"].astype(str), cohort["fifa_code"].astype(str)))
    code_to_team = {code: team for team, code in team_to_code.items()}
    folded_to_team = {team.casefold(): team for team in team_to_code}

    if "team" in data.columns:
        data["team"] = data["team"].astype("string").str.strip()
        canonical_teams = data["team"].str.casefold().map(folded_to_team)
        changed = canonical_teams.notna() & data["team"].ne(canonical_teams)
        if changed.any() and "team_source" not in data.columns:
            data["team_source"] = data["team"]
        data.loc[canonical_teams.notna(), "team"] = canonical_teams
    if "fifa_code" in data.columns:
        data["fifa_code"] = data["fifa_code"].astype("string").str.strip().str.upper()
    if "team" not in data.columns and "fifa_code" in data.columns:
        data["team"] = data["fifa_code"].map(code_to_team).astype("string")
    if "fifa_code" not in data.columns and "team" in data.columns:
        data["fifa_code"] = data["team"].map(team_to_code).astype("string")

    if "season_end_year" not in data.columns and "season" in data.columns:
        data["season_end_year"] = data["season"].map(parse_season_end_year)
    if "season" not in data.columns and "season_end_year" in data.columns:
        parsed_years = pd.to_numeric(data["season_end_year"], errors="coerce")
        data["season"] = parsed_years.map(lambda year: season_label(int(year)) if pd.notna(year) else pd.NA)

    if "player_name" in data.columns:
        data["player_name"] = data["player_name"].astype("string").str.strip()
    if "player_id" not in data.columns:
        data["player_id"] = pd.NA
    urls = data["player_url"] if "player_url" in data.columns else pd.Series(pd.NA, index=data.index)
    dobs = data["dob"] if "dob" in data.columns else pd.Series(pd.NA, index=data.index)
    missing_ids = data["player_id"].isna() | data["player_id"].astype("string").str.strip().eq("")
    generated = [stable_player_id(name, url, dob) for name, url, dob in zip(data.get("player_name", []), urls, dobs)]
    if len(generated) == len(data):
        data.loc[missing_ids, "player_id"] = pd.Series(generated, index=data.index)[missing_ids]
    data["player_id"] = data["player_id"].astype("string").str.strip()

    for column, default in (("sub_appearances", None), ("goals", 0)):
        if column not in data.columns and default is not None:
            data[column] = default
    for column in ("player_url", "position_source", "source_url", "retrieved_at"):
        if column not in data.columns:
            data[column] = pd.NA

    for column in REQUIRED_COLUMNS:
        if column not in data.columns:
            _issue(issues, "error", "missing_column", None, column, None, f"Required column '{column}' is missing")

    numeric_columns = [
        column
        for column in ("season_end_year", "starts", "sub_appearances", "goals", "expected_matches")
        if column in data
    ]
    for column in numeric_columns:
        original = data[column]
        numeric = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & numeric.isna()
        fractional = numeric.notna() & numeric.mod(1).ne(0)
        for index in data.index[invalid | fractional]:
            _issue(
                issues,
                "error",
                "invalid_integer",
                int(data.at[index, "_input_row"]),
                column,
                original.at[index],
                f"'{column}' must be a whole number",
            )
        data[column] = numeric.astype("Int64")

    for column in REQUIRED_COLUMNS:
        if column not in data.columns:
            continue
        missing = data[column].isna()
        if pd.api.types.is_string_dtype(data[column]):
            missing |= data[column].astype("string").str.strip().eq("")
        for index in data.index[missing]:
            _issue(
                issues,
                "error",
                "missing_value",
                int(data.at[index, "_input_row"]),
                column,
                data.at[index, column],
                f"'{column}' cannot be blank",
            )

    for column in ("starts", "sub_appearances", "goals", "expected_matches"):
        if column not in data.columns:
            continue
        for index in data.index[data[column].lt(0).fillna(False)]:
            _issue(
                issues,
                "error",
                "negative_count",
                int(data.at[index, "_input_row"]),
                column,
                data.at[index, column],
                f"'{column}' cannot be negative",
            )

    if "team" in data.columns:
        unknown = data["team"].notna() & ~data["team"].isin(team_to_code)
        for index in data.index[unknown]:
            _issue(issues, "error", "unknown_team", int(data.at[index, "_input_row"]), "team", data.at[index, "team"], "Team is not in the frozen top-20 cohort")
    if "fifa_code" in data.columns:
        unknown = data["fifa_code"].notna() & ~data["fifa_code"].isin(code_to_team)
        for index in data.index[unknown]:
            _issue(issues, "error", "unknown_fifa_code", int(data.at[index, "_input_row"]), "fifa_code", data.at[index, "fifa_code"], "FIFA code is not in the frozen top-20 cohort")
    if "team" in data.columns and "fifa_code" in data.columns:
        expected = data["team"].map(team_to_code)
        mismatch = expected.notna() & data["fifa_code"].notna() & expected.ne(data["fifa_code"])
        for index in data.index[mismatch]:
            _issue(issues, "error", "team_code_mismatch", int(data.at[index, "_input_row"]), "fifa_code", data.at[index, "fifa_code"], f"Expected {expected.at[index]} for {data.at[index, 'team']}")

    if "season_end_year" in data.columns:
        outside = data["season_end_year"].notna() & ~data["season_end_year"].between(MIN_SEASON_END_YEAR, MAX_SEASON_END_YEAR)
        for index in data.index[outside]:
            _issue(issues, "error", "season_out_of_scope", int(data.at[index, "_input_row"]), "season_end_year", data.at[index, "season_end_year"], f"Season end year must be {MIN_SEASON_END_YEAR}-{MAX_SEASON_END_YEAR}")
    if "season" in data.columns and "season_end_year" in data.columns:
        source_seasons = data["season"].copy()
        parsed_seasons = source_seasons.map(parse_season_end_year)
        invalid = source_seasons.notna() & parsed_seasons.isna()
        for index in data.index[invalid]:
            _issue(issues, "error", "invalid_season", int(data.at[index, "_input_row"]), "season", source_seasons.at[index], "Season must look like 2005-06, 2005/06, or an end year")
        expected_labels = data["season_end_year"].map(lambda year: season_label(int(year)) if pd.notna(year) else pd.NA)
        mismatch = parsed_seasons.notna() & data["season_end_year"].notna() & parsed_seasons.ne(data["season_end_year"])
        for index in data.index[mismatch]:
            _issue(issues, "error", "season_mismatch", int(data.at[index, "_input_row"]), "season", source_seasons.at[index], f"Season text does not match end year {data.at[index, 'season_end_year']}")
        changed = source_seasons.notna() & expected_labels.notna() & source_seasons.astype("string").str.strip().ne(expected_labels)
        if changed.any() and "season_source" not in data.columns:
            data["season_source"] = source_seasons
        data.loc[parsed_seasons.notna() & expected_labels.notna(), "season"] = expected_labels

    duplicate_key = [column for column in ("team", "season_end_year", "player_id") if column in data.columns]
    if len(duplicate_key) == 3:
        duplicate = data.duplicated(duplicate_key, keep=False) & data[duplicate_key].notna().all(axis=1)
        for index in data.index[duplicate]:
            _issue(issues, "error", "duplicate_team_season_player", int(data.at[index, "_input_row"]), None, None, "Duplicate team-season-player row")

    canonical = [column for column in CANONICAL_COLUMNS if column in data.columns]
    extras = [column for column in data.columns if column not in canonical and column != "_input_row"]
    data = data[canonical + extras]
    issue_frame = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    return ValidationResult(data=data, issues=issue_frame)
