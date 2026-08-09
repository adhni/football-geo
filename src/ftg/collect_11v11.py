from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import requests

from .http_cache import CachedHttpClient
from .parse_11v11 import parse_team_season_html, rows_as_dicts
from .schema import (
    MAX_SEASON_END_YEAR,
    MIN_SEASON_END_YEAR,
    normalize_player_seasons,
    season_label,
    stable_player_id,
)

ROOT = Path(__file__).resolve().parents[2]
TEAM_CONFIG = ROOT / "config" / "top20_fifa_2026-07-20.csv"
RAW = ROOT / "data" / "raw" / "11v11"
PROCESSED = ROOT / "data" / "processed"
FRAGMENTS = PROCESSED / "11v11_team_seasons"
QA = ROOT / "data" / "qa"

OUTPUT_COLUMNS = [
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


def team_season_url(slug: str, end_year: int) -> str:
    return f"https://www.11v11.com/teams/{slug}/tab/players/season/{end_year}/"


def _fragment_path(fifa_code: str, end_year: int) -> Path:
    return FRAGMENTS / fifa_code / f"{end_year}.parquet"


def _write_fragment(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp.parquet")
    frame.to_parquet(temp, index=False)
    temp.replace(path)


def _all_fragments() -> pd.DataFrame:
    paths = sorted(FRAGMENTS.glob("*/*.parquet"))
    if not paths:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    return pd.concat((pd.read_parquet(path) for path in paths), ignore_index=True, sort=False)


def run(
    start_season: int,
    end_season: int,
    delay: float = 1.5,
    teams: list[str] | None = None,
    *,
    retries: int = 3,
    force: bool = False,
) -> pd.DataFrame:
    if start_season > end_season:
        raise ValueError("start-season cannot be after end-season")
    if start_season < MIN_SEASON_END_YEAR or end_season > MAX_SEASON_END_YEAR:
        raise ValueError(
            f"Season end years must be within {MIN_SEASON_END_YEAR}-{MAX_SEASON_END_YEAR}"
        )
    cohort = pd.read_csv(TEAM_CONFIG)
    selected = cohort
    if teams:
        wanted = {team.casefold() for team in teams}
        selected = cohort[cohort["team"].str.casefold().isin(wanted)]
        missing = sorted(wanted - set(selected["team"].str.casefold()))
        if missing:
            raise ValueError(f"Unknown team selection: {', '.join(missing)}")

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "football-talent-geography/0.2 (research; respectful cached crawler)"}
    )
    client = CachedHttpClient(session, delay=delay, retries=retries)
    crawl_issues: list[dict] = []

    for team in selected.itertuples(index=False):
        for end_year in range(start_season, end_season + 1):
            fragment_path = _fragment_path(team.fifa_code, end_year)
            if fragment_path.exists() and not force:
                if pd.read_parquet(fragment_path).empty:
                    crawl_issues.append(
                        {
                            "team": team.team,
                            "fifa_code": team.fifa_code,
                            "season_end_year": end_year,
                            "source_url": team_season_url(team.elevenv11_slug, end_year),
                            "issue": "cached_fragment_has_no_rows",
                        }
                    )
                continue
            url = team_season_url(team.elevenv11_slug, end_year)
            result = client.fetch_text(url, RAW / team.fifa_code / f"{end_year}.html", force=force)
            parsed = parse_team_season_html(result.text)
            if not parsed:
                crawl_issues.append(
                    {
                        "team": team.team,
                        "fifa_code": team.fifa_code,
                        "season_end_year": end_year,
                        "source_url": url,
                        "issue": "no_player_table_or_rows",
                    }
                )
            records: list[dict] = []
            for row in rows_as_dicts(parsed):
                records.append(
                    {
                        "team": team.team,
                        "fifa_code": team.fifa_code,
                        "season": season_label(end_year),
                        "season_end_year": end_year,
                        "player_id": stable_player_id(row["player_name"], row["player_url"]),
                        "player_name": row["player_name"],
                        "player_url": row["player_url"],
                        "starts": row["starts"],
                        "sub_appearances": row["sub_appearances"],
                        "goals": row["goals"],
                        "position_source": row["position"],
                        "source_url": url,
                        "retrieved_at": result.retrieved_at,
                    }
                )
            _write_fragment(pd.DataFrame(records, columns=OUTPUT_COLUMNS), fragment_path)

    combined = _all_fragments()
    validation = normalize_player_seasons(combined, cohort)
    QA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        crawl_issues,
        columns=["team", "fifa_code", "season_end_year", "source_url", "issue"],
    ).to_csv(QA / "collect_11v11_issues.csv", index=False)
    validation.issues.to_csv(QA / "collect_11v11_validation.csv", index=False)
    if validation.has_errors:
        raise RuntimeError(f"Collected data failed validation; review {QA / 'collect_11v11_validation.csv'}")

    PROCESSED.mkdir(parents=True, exist_ok=True)
    output = PROCESSED / "player_season_starts.parquet"
    validation.data.to_parquet(output, index=False)
    print(f"Wrote {len(validation.data):,} accumulated rows to {output}")
    if crawl_issues:
        print(f"Flagged {len(crawl_issues):,} empty team-season pages in {QA}")
    return validation.data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-season", type=int, default=2000, help="season END year, e.g. 2000 = 1999-00")
    parser.add_argument("--end-season", type=int, default=2026)
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--team", action="append", dest="teams")
    parser.add_argument("--force", action="store_true", help="refetch and reparse existing cached pages")
    args = parser.parse_args()
    run(args.start_season, args.end_season, args.delay, args.teams, retries=args.retries, force=args.force)


if __name__ == "__main__":
    main()
