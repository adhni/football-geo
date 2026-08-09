from __future__ import annotations

"""Wikidata enrichment scaffold.

This module intentionally requires explicit, cached entity resolution rather than
silently guessing. It uses the MediaWiki search API, then validates candidate DOB.
Extend it with SPARQL or entity-data lookups in Codex once the Italy pilot is running.
"""

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CACHE = ROOT / "data" / "raw" / "wikidata"
QA = ROOT / "data" / "processed" / "qa"

API = "https://www.wikidata.org/w/api.php"


def search_candidates(session: requests.Session, name: str) -> list[dict]:
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "limit": 8,
        "type": "item",
    }
    return session.get(API, params=params, timeout=30).json().get("search", [])


def run() -> None:
    players = pd.read_parquet(PROCESSED / "players_source.parquet")
    CACHE.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "football-talent-geography/0.1"})
    unresolved = []
    for row in players.itertuples(index=False):
        path = CACHE / f"{row.player_id}_search.json"
        if path.exists():
            candidates = json.loads(path.read_text())
        else:
            candidates = search_candidates(session, row.player_name)
            path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2))
        unresolved.append({
            "player_id": row.player_id,
            "player_name": row.player_name,
            "dob": str(row.dob) if pd.notna(row.dob) else None,
            "birthplace_text": row.birthplace_text,
            "candidate_qids": ";".join(c.get("id", "") for c in candidates),
            "status": "needs_dob_validated_resolution",
        })
    pd.DataFrame(unresolved).to_csv(QA / "wikidata_resolution_queue.csv", index=False)
    print("Created QA resolution queue. Codex should add DOB-validated auto-resolution before using QIDs.")


if __name__ == "__main__":
    run()
