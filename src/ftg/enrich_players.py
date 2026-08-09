from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "11v11_players"
QA = ROOT / "data" / "qa"


def parse_profile(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    def find(label: str) -> str | None:
        match = re.search(rf"{re.escape(label)}\s*:?\s*\n?\s*([^\n]+)", text, flags=re.I)
        return match.group(1).strip() if match else None

    return {
        "dob_source": find("Date of birth"),
        "birthplace_text": find("Place of birth"),
        "nationality_source": find("Nationality"),
        "position_profile": find("Position"),
    }


def run(delay: float = 1.5, retries: int = 3, force: bool = False) -> pd.DataFrame:
    starts = pd.read_parquet(PROCESSED / "player_season_starts.parquet")
    source_players = starts[["player_id", "player_name", "player_url"]].drop_duplicates()
    conflicts = source_players.groupby("player_id", dropna=False).size().loc[lambda counts: counts > 1]
    players = source_players.sort_values(["player_id", "player_name"]).drop_duplicates("player_id")

    session = requests.Session()
    session.headers.update({"User-Agent": "football-talent-geography/0.2 (research; cached crawler)"})
    client = CachedHttpClient(session, delay=delay, retries=retries)
    records: list[dict] = []
    issues: list[dict] = [
        {
            "player_id": player_id,
            "player_name": None,
            "issue": "conflicting_source_identity",
            "detail": f"{count} name/URL combinations share this player_id",
        }
        for player_id, count in conflicts.items()
    ]
    for row in players.itertuples(index=False):
        base = {"player_id": row.player_id, "player_name": row.player_name, "player_url": row.player_url}
        if not row.player_url or pd.isna(row.player_url):
            records.append({**base, "retrieved_at": None})
            issues.append({**base, "issue": "missing_player_url", "detail": None})
            continue
        result = client.fetch_text(row.player_url, RAW / f"{row.player_id}.html", force=force)
        metadata = parse_profile(result.text)
        records.append({**base, **metadata, "retrieved_at": result.retrieved_at})
        for field in ("dob_source", "birthplace_text"):
            if not metadata[field]:
                issues.append({**base, "issue": f"missing_{field}", "detail": None})

    output = pd.DataFrame(records)
    output["dob"] = pd.to_datetime(output.get("dob_source"), errors="coerce", dayfirst=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    output.to_parquet(PROCESSED / "players_source.parquet", index=False)
    pd.DataFrame(
        issues,
        columns=["player_id", "player_name", "player_url", "issue", "detail"],
    ).to_csv(QA / "player_profile_issues.csv", index=False)
    print(f"Wrote {len(output):,} unique player profiles")
    print(f"Flagged {len(issues):,} profile QA issues")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=float, default=1.5)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(args.delay, args.retries, args.force)


if __name__ == "__main__":
    main()
