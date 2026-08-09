from __future__ import annotations

import argparse
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .parse_11v11 import parse_team_season_html, rows_as_dicts

ROOT = Path(__file__).resolve().parents[2]
TEAM_CONFIG = ROOT / "config" / "top20_fifa_2026-07-20.csv"
RAW = ROOT / "data" / "raw" / "11v11"
PROCESSED = ROOT / "data" / "processed"


def season_label(end_year: int) -> str:
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def team_season_url(slug: str, end_year: int) -> str:
    return f"https://www.11v11.com/teams/{slug}/tab/players/season/{end_year}/"


def fetch(session: requests.Session, url: str, path: Path, delay: float, retries: int = 3) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            path.write_text(r.text, encoding="utf-8")
            time.sleep(delay)
            return r.text
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(delay * (attempt + 1))
    raise RuntimeError(f"Failed after {retries} attempts: {url}") from last_exc


def run(start_season: int, end_season: int, delay: float = 1.5, teams: list[str] | None = None) -> pd.DataFrame:
    cfg = pd.read_csv(TEAM_CONFIG)
    if teams:
        wanted = {t.lower() for t in teams}
        cfg = cfg[cfg["team"].str.lower().isin(wanted)]
    session = requests.Session()
    session.headers.update({
        "User-Agent": "football-talent-geography/0.1 (research; respectful cached crawler)"
    })
    records: list[dict] = []
    for _, team in cfg.iterrows():
        for end_year in range(start_season, end_season + 1):
            url = team_season_url(team.elevenv11_slug, end_year)
            html_path = RAW / team.fifa_code / f"{end_year}.html"
            html = fetch(session, url, html_path, delay)
            parsed = parse_team_season_html(html)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            for row in rows_as_dicts(parsed):
                player_key = row.get("player_url") or f"{team.team}|{row['player_name']}"
                player_id = hashlib.sha1(player_key.encode("utf-8")).hexdigest()[:16]
                records.append({
                    "team": team.team,
                    "fifa_code": team.fifa_code,
                    "season": season_label(end_year),
                    "season_end_year": end_year,
                    "player_id": player_id,
                    "player_name": row["player_name"],
                    "player_url": row["player_url"],
                    "starts": row["starts"],
                    "sub_appearances": row["sub_appearances"],
                    "goals": row["goals"],
                    "position_source": row["position"],
                    "source_url": url,
                    "retrieved_at": retrieved_at,
                })
    df = pd.DataFrame(records)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "player_season_starts.parquet"
    df.to_parquet(out, index=False)
    print(f"Wrote {len(df):,} rows to {out}")
    return df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--start-season", type=int, default=2000, help="season END year, e.g. 2000 = 1999-00")
    p.add_argument("--end-season", type=int, default=2026)
    p.add_argument("--delay", type=float, default=1.5)
    p.add_argument("--team", action="append", dest="teams")
    a = p.parse_args()
    run(a.start_season, a.end_season, a.delay, a.teams)


if __name__ == "__main__":
    main()
