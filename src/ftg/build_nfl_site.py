from __future__ import annotations

import argparse
import csv
import io
import json
import re
import time
import unicodedata
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

from src.ftg.http_cache import CachedHttpClient

ROOT = Path(__file__).resolve().parents[2]
SNAPS_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2025.csv"
PLAYERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
ESPN_ATHLETE_URL = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/athletes/{athlete_id}?lang=en&region=us"
GEONAMES_CITIES_URL = "https://download.geonames.org/export/dump/cities500.zip"
GEONAMES_COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"

DEFAULT_OUTPUT = ROOT / "docs" / "nfl" / "data" / "dashboard.json"
DEFAULT_SNAPS_CACHE = ROOT / "data" / "cache" / "nfl_snap_counts_2025.csv"
DEFAULT_PLAYERS_CACHE = ROOT / "data" / "cache" / "nfl_players.csv"
DEFAULT_ESPN_CACHE = ROOT / "data" / "cache" / "nfl_espn_athletes_2025.json"
DEFAULT_GEONAMES_CACHE = ROOT / "data" / "cache" / "cities500.zip"
DEFAULT_COUNTRIES_CACHE = ROOT / "data" / "cache" / "geonames_country_info.txt"

TEAM_META = {
    "ARI": ("Arizona Cardinals", "NFC", "NFC West"),
    "ATL": ("Atlanta Falcons", "NFC", "NFC South"),
    "BAL": ("Baltimore Ravens", "AFC", "AFC North"),
    "BUF": ("Buffalo Bills", "AFC", "AFC East"),
    "CAR": ("Carolina Panthers", "NFC", "NFC South"),
    "CHI": ("Chicago Bears", "NFC", "NFC North"),
    "CIN": ("Cincinnati Bengals", "AFC", "AFC North"),
    "CLE": ("Cleveland Browns", "AFC", "AFC North"),
    "DAL": ("Dallas Cowboys", "NFC", "NFC East"),
    "DEN": ("Denver Broncos", "AFC", "AFC West"),
    "DET": ("Detroit Lions", "NFC", "NFC North"),
    "GB": ("Green Bay Packers", "NFC", "NFC North"),
    "HOU": ("Houston Texans", "AFC", "AFC South"),
    "IND": ("Indianapolis Colts", "AFC", "AFC South"),
    "JAX": ("Jacksonville Jaguars", "AFC", "AFC South"),
    "KC": ("Kansas City Chiefs", "AFC", "AFC West"),
    "LA": ("Los Angeles Rams", "NFC", "NFC West"),
    "LAC": ("Los Angeles Chargers", "AFC", "AFC West"),
    "LV": ("Las Vegas Raiders", "AFC", "AFC West"),
    "MIA": ("Miami Dolphins", "AFC", "AFC East"),
    "MIN": ("Minnesota Vikings", "NFC", "NFC North"),
    "NE": ("New England Patriots", "AFC", "AFC East"),
    "NO": ("New Orleans Saints", "NFC", "NFC South"),
    "NYG": ("New York Giants", "NFC", "NFC East"),
    "NYJ": ("New York Jets", "AFC", "AFC East"),
    "PHI": ("Philadelphia Eagles", "NFC", "NFC East"),
    "PIT": ("Pittsburgh Steelers", "AFC", "AFC North"),
    "SEA": ("Seattle Seahawks", "NFC", "NFC West"),
    "SF": ("San Francisco 49ers", "NFC", "NFC West"),
    "TB": ("Tampa Bay Buccaneers", "NFC", "NFC South"),
    "TEN": ("Tennessee Titans", "AFC", "AFC South"),
    "WAS": ("Washington Commanders", "NFC", "NFC East"),
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def _download_binary(url: str, path: Path, *, force: bool = False) -> Path:
    if path.exists() and not force:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with requests.get(url, timeout=120, stream=True, headers={"User-Agent": "TalentGeography/1.0"}) as response:
        response.raise_for_status()
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(1024 * 1024):
                handle.write(chunk)
    temporary.replace(path)
    return path


def load_csv(url: str, cache_path: Path, input_path: Path | None = None, *, force: bool = False) -> pd.DataFrame:
    if input_path:
        return pd.read_csv(input_path)
    result = CachedHttpClient(delay=0.0, timeout=90).fetch_text(url, cache_path, force=force)
    return pd.read_csv(io.StringIO(result.text))


def aggregate_snap_cohort(snaps: pd.DataFrame) -> list[dict[str, Any]]:
    required = {
        "game_id", "game_type", "pfr_player_id", "player", "position", "team",
        "offense_snaps", "defense_snaps", "st_snaps",
    }
    if missing := required - set(snaps.columns):
        raise ValueError(f"NFL snap export is missing columns: {', '.join(sorted(missing))}")
    regular = snaps[snaps["game_type"].eq("REG") & snaps["pfr_player_id"].notna()].copy()
    regular["total_snaps"] = regular[["offense_snaps", "defense_snaps", "st_snaps"]].fillna(0).sum(axis=1)
    regular = regular[regular["total_snaps"] > 0]
    cohort = []
    for player_id, rows in regular.groupby("pfr_player_id", sort=True):
        team_snaps = rows.groupby("team")["total_snaps"].sum().sort_values(ascending=False)
        position = rows["position"].dropna().astype(str).mode()
        names = rows["player"].dropna().astype(str).mode()
        cohort.append(
            {
                "pfr_id": str(player_id),
                "snap_name": names.iloc[0] if len(names) else str(player_id),
                "snap_position": position.iloc[0] if len(position) else None,
                "team_code": str(team_snaps.index[0]),
                "team_codes": [str(team) for team in team_snaps.index],
                "games": int(rows["game_id"].nunique()),
                "snaps": int(rows["total_snaps"].sum()),
                "offense_snaps": int(rows["offense_snaps"].fillna(0).sum()),
                "defense_snaps": int(rows["defense_snaps"].fillna(0).sum()),
                "special_teams_snaps": int(rows["st_snaps"].fillna(0).sum()),
            }
        )
    return cohort


def _athlete_summary(payload: dict[str, Any]) -> dict[str, Any]:
    birth = payload.get("birthPlace") or {}
    return {
        "name": payload.get("displayName"),
        "birth_city": birth.get("city"),
        "birth_state": birth.get("state"),
        "birth_country": birth.get("country"),
        "dob": str(payload.get("dateOfBirth") or "")[:10] or None,
    }


def fetch_espn_athletes(
    athlete_ids: Iterable[str],
    cache_path: Path = DEFAULT_ESPN_CACHE,
    *,
    workers: int = 10,
    force: bool = False,
) -> dict[str, dict[str, Any]]:
    cache: dict[str, dict[str, Any]] = {}
    if cache_path.exists() and not force:
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    ids = sorted({str(athlete_id) for athlete_id in athlete_ids if athlete_id and str(athlete_id) != "<NA>"})
    missing = ids if force else [athlete_id for athlete_id in ids if athlete_id not in cache]

    def fetch_one(athlete_id: str) -> tuple[str, dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(
                    ESPN_ATHLETE_URL.format(athlete_id=athlete_id),
                    timeout=30,
                    headers={"User-Agent": "TalentGeography/1.0"},
                )
                response.raise_for_status()
                return athlete_id, _athlete_summary(response.json())
            except (requests.RequestException, ValueError) as error:
                last_error = error
                time.sleep(0.4 * (attempt + 1))
        return athlete_id, {"error": str(last_error)}

    if missing:
        print(f"Fetching {len(missing):,} ESPN athlete profiles...", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(fetch_one, athlete_id) for athlete_id in missing]
            for index, future in enumerate(as_completed(futures), start=1):
                athlete_id, result = future.result()
                cache[athlete_id] = result
                if index % 100 == 0 or index == len(missing):
                    _write_json(cache_path, cache)
                    print(f"  fetched {index:,}/{len(missing):,}", flush=True)
    return cache


def load_country_codes(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    aliases: dict[str, str] = {}
    names: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 5:
            continue
        iso, iso3, _, fips, country = fields[:5]
        names[iso] = country
        for value in (iso, iso3, fips, country):
            if value:
                aliases[normalize(value)] = iso
    aliases.update({"usa": "US", "unitedstatesofamerica": "US", "uk": "GB"})
    return aliases, names


def build_city_index(cities_zip: Path, needed_names: set[str]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with zipfile.ZipFile(cities_zip) as archive, archive.open("cities500.txt") as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"), delimiter="\t")
        for fields in reader:
            if len(fields) < 19:
                continue
            aliases = {normalize(fields[1]), normalize(fields[2])}
            aliases.update(normalize(value) for value in fields[3].split(",") if value)
            matches = aliases & needed_names
            if not matches:
                continue
            candidate = {
                "name": fields[1],
                "lat": float(fields[4]),
                "lon": float(fields[5]),
                "country_code": fields[8],
                "admin1": fields[10],
                "population": int(fields[14] or 0),
                "geonames_id": fields[0],
            }
            for alias in matches:
                index[alias].append(candidate)
    return dict(index)


def resolve_birthplace(
    athlete: dict[str, Any],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
) -> dict[str, Any] | None:
    city = athlete.get("birth_city")
    if not city:
        return None
    candidates = city_index.get(normalize(city), [])
    country_code = country_aliases.get(normalize(athlete.get("birth_country")))
    if country_code:
        candidates = [candidate for candidate in candidates if candidate["country_code"] == country_code]
    state = str(athlete.get("birth_state") or "").upper()
    if country_code == "US" and state:
        candidates = [candidate for candidate in candidates if candidate["admin1"].upper() == state]
    if not candidates:
        return None
    match = max(candidates, key=lambda candidate: candidate["population"])
    return {
        "place": str(city),
        "country": country_names.get(match["country_code"], athlete.get("birth_country") or match["country_code"]),
        "lat": round(match["lat"], 6),
        "lon": round(match["lon"], 6),
        "geonames_id": match["geonames_id"],
    }


def age_on(dob: str | None, on_date: date = date(2026, 2, 8)) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))


def build_payload(
    snaps: pd.DataFrame,
    players: pd.DataFrame,
    athletes: dict[str, dict[str, Any]],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    cohort = aggregate_snap_cohort(snaps)
    player_lookup = {
        str(row.pfr_id): row
        for row in players[players["pfr_id"].notna()].drop_duplicates("pfr_id").itertuples(index=False)
    }
    records = []
    unresolved = []
    for snap in cohort:
        player = player_lookup.get(snap["pfr_id"])
        espn_id = None
        if player is not None and pd.notna(getattr(player, "espn_id", None)):
            espn_id = str(int(float(player.espn_id)))
        athlete = athletes.get(espn_id, {}) if espn_id else {}
        birthplace = resolve_birthplace(athlete, city_index, country_aliases, country_names)
        mapped = birthplace is not None
        status = "resolved" if mapped else (
            "player identity unavailable" if player is None
            else "birth city unavailable" if not athlete.get("birth_city")
            else "birth city coordinates unavailable"
        )
        team_code = snap["team_code"]
        team, conference, division = TEAM_META[team_code]
        dob = athlete.get("dob") or (str(player.birth_date)[:10] if player is not None and pd.notna(player.birth_date) else None)
        name = str(player.display_name) if player is not None and pd.notna(player.display_name) else snap["snap_name"]
        position = str(player.position) if player is not None and pd.notna(player.position) else snap["snap_position"]
        college = str(player.college_name) if player is not None and pd.notna(player.college_name) else None
        record = {
            "id": f"nfl:{snap['pfr_id']}",
            "pfrId": snap["pfr_id"],
            "espnId": espn_id,
            "name": name,
            "team": team,
            "teamCode": team_code,
            "teams": [TEAM_META[code][0] for code in snap["team_codes"] if code in TEAM_META],
            "conference": conference,
            "division": division,
            "year": 2025,
            "games": snap["games"],
            "snaps": snap["snaps"],
            "offenseSnaps": snap["offense_snaps"],
            "defenseSnaps": snap["defense_snaps"],
            "specialTeamsSnaps": snap["special_teams_snaps"],
            "position": position,
            "college": college,
            "age": age_on(dob),
            "dob": dob,
            "place": birthplace["place"] if mapped else None,
            "country": birthplace["country"] if mapped else None,
            "lat": birthplace["lat"] if mapped else None,
            "lon": birthplace["lon"] if mapped else None,
            "mapped": mapped,
            "status": status,
            "geonamesId": birthplace["geonames_id"] if mapped else None,
        }
        records.append(record)
        if not mapped:
            unresolved.append({"name": name, "status": status})

    records.sort(key=lambda record: (record["team"], record["name"]))
    mapped_records = [record for record in records if record["mapped"]]
    total_snaps = sum(record["snaps"] for record in records)
    mapped_snaps = sum(record["snaps"] for record in mapped_records)
    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return {
        "meta": {
            "title": "NFL Talent Geography",
            "sport": "nfl",
            "scope": "2025 NFL regular season",
            "season": "2025",
            "year": 2025,
            "teams": [TEAM_META[code][0] for code in TEAM_META],
            "conferences": ["AFC", "NFC"],
            "divisions": sorted({value[2] for value in TEAM_META.values()}),
            "generated_at": generated_at,
            "snaps_source_name": "nflverse snap counts",
            "snaps_source_url": SNAPS_URL,
            "birthplace_source_name": "ESPN athlete profiles",
            "coordinate_source_name": "GeoNames",
        },
        "summary": {
            "teams": len({record["team"] for record in records}),
            "players": len(records),
            "mapped_players": len(mapped_records),
            "player_coverage_pct": round(len(mapped_records) / len(records) * 100, 1) if records else 0,
            "snaps": total_snaps,
            "mapped_snaps": mapped_snaps,
            "snap_coverage_pct": round(mapped_snaps / total_snaps * 100, 1) if total_snaps else 0,
            "birthplaces": len({(record["lat"], record["lon"], record["place"]) for record in mapped_records}),
            "birth_countries": len({record["country"] for record in mapped_records}),
            "unresolved_players": len(unresolved),
        },
        "records": records,
        "unresolved": unresolved,
    }


def run(
    snaps_input: Path | None = None,
    players_input: Path | None = None,
    geonames_input: Path | None = None,
    countries_input: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    workers: int = 10,
    force: bool = False,
) -> dict[str, Any]:
    snaps = load_csv(SNAPS_URL, DEFAULT_SNAPS_CACHE, snaps_input, force=force)
    players = load_csv(PLAYERS_URL, DEFAULT_PLAYERS_CACHE, players_input, force=force)
    cohort = aggregate_snap_cohort(snaps)
    player_ids = {row["pfr_id"] for row in cohort}
    master = players[players["pfr_id"].astype(str).isin(player_ids) & players["espn_id"].notna()]
    athlete_ids = [str(int(float(value))) for value in master["espn_id"]]
    athletes = fetch_espn_athletes(athlete_ids, workers=workers, force=force)
    needed_names = {normalize(row.get("birth_city")) for row in athletes.values() if row.get("birth_city")}
    cities_path = geonames_input or _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=force)
    countries_path = countries_input
    if countries_path is None:
        CachedHttpClient(delay=0.0, timeout=90).fetch_text(
            GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=force
        )
        countries_path = DEFAULT_COUNTRIES_CACHE
    country_aliases, country_names = load_country_codes(countries_path)
    city_index = build_city_index(cities_path, needed_names)
    payload = build_payload(snaps, players, athletes, city_index, country_aliases, country_names)
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']:,} NFL players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% birthplace coverage to {output_path}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the static NFL talent geography dataset")
    parser.add_argument("--snaps-input", type=Path)
    parser.add_argument("--players-input", type=Path)
    parser.add_argument("--geonames-input", type=Path)
    parser.add_argument("--countries-input", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run(
        args.snaps_input,
        args.players_input,
        args.geonames_input,
        args.countries_input,
        args.output,
        workers=args.workers,
        force=args.force,
    )


if __name__ == "__main__":
    main()
