from __future__ import annotations

import argparse
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw" / "11v11_players"


def parse_profile(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    def find(label: str) -> str | None:
        m = re.search(rf"{re.escape(label)}\s*\n?\s*([^\n]+)", text, flags=re.I)
        return m.group(1).strip() if m else None
    return {
        "dob_source": find("Date of birth"),
        "birthplace_text": find("Place of birth"),
        "nationality_source": find("Nationality"),
        "position_profile": find("Position"),
    }


def run(delay: float = 1.5) -> pd.DataFrame:
    starts = pd.read_parquet(PROCESSED / "player_season_starts.parquet")
    players = starts[["player_id", "player_name", "player_url"]].drop_duplicates()
    session = requests.Session()
    session.headers.update({"User-Agent": "football-talent-geography/0.1 (research; cached crawler)"})
    records = []
    for row in players.itertuples(index=False):
        if not row.player_url:
            records.append({"player_id": row.player_id, "player_name": row.player_name, "player_url": None})
            continue
        path = RAW / f"{row.player_id}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            html = path.read_text(encoding="utf-8", errors="replace")
        else:
            r = session.get(row.player_url, timeout=30)
            r.raise_for_status()
            html = r.text
            path.write_text(html, encoding="utf-8")
            time.sleep(delay)
        meta = parse_profile(html)
        records.append({
            "player_id": row.player_id,
            "player_name": row.player_name,
            "player_url": row.player_url,
            **meta,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        })
    out_df = pd.DataFrame(records)
    out_df["dob"] = pd.to_datetime(out_df.get("dob_source"), errors="coerce", dayfirst=True)
    out_df.to_parquet(PROCESSED / "players_source.parquet", index=False)
    print(f"Wrote {len(out_df):,} unique player profiles")
    return out_df


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--delay", type=float, default=1.5)
    a = p.parse_args()
    run(a.delay)


if __name__ == "__main__":
    main()
