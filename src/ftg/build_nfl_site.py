from __future__ import annotations

import argparse
import io
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

from src.ftg.geonames import (
    DEFAULT_COUNTRIES_CACHE,
    DEFAULT_GEONAMES_CACHE,
    GEONAMES_CITIES_URL,
    GEONAMES_COUNTRIES_URL,
    build_city_index,
    load_country_codes,
    resolve_birthplace,
)
from src.ftg.http_cache import CachedHttpClient
from src.ftg.utils import (
    age_on as _age_on,
    download_binary as _download_binary,
    normalize_key as normalize,
    write_json as _write_json,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPS_URL = "https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_2025.csv"
PLAYERS_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
ESPN_ATHLETE_URL = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/athletes/{athlete_id}?lang=en&region=us"
ESPN_COLLEGE_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams?limit=1000"
ESPN_COLLEGE_SCHEDULE_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{team_id}/schedule?season=2025"

DEFAULT_OUTPUT = ROOT / "docs" / "nfl" / "data" / "dashboard.json"
DEFAULT_SNAPS_CACHE = ROOT / "data" / "cache" / "nfl_snap_counts_2025.csv"
DEFAULT_PLAYERS_CACHE = ROOT / "data" / "cache" / "nfl_players.csv"
DEFAULT_ESPN_CACHE = ROOT / "data" / "cache" / "nfl_espn_athletes_2025.json"
DEFAULT_COLLEGE_TEAMS_CACHE = ROOT / "data" / "cache" / "nfl_espn_college_teams.json"
DEFAULT_COLLEGE_VENUES_CACHE = ROOT / "data" / "cache" / "nfl_espn_college_venues_2025.json"

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

# nflverse uses several historical or long-form school labels. Values here are
# ESPN's current athletic-program labels; no player is assigned to a different
# school, and unresolved names remain in the QA output.
COLLEGE_ALIASES = {
    "Mississippi": "Ole Miss",
    "Louisiana-Lafayette": "Louisiana",
    "Texas-El Paso": "UTEP",
    "Southern Mississippi": "Southern Miss",
    "Connecticut": "UConn",
    "Appalachian State": "App State",
    "Middle Tennessee State": "Middle Tennessee",
    "Texas-San Antonio": "UTSA",
    "University of South Florida": "South Florida",
    "UMass Amherst": "UMass",
    "Tennessee-Chattanooga": "Chattanooga",
    "Southern Utah State": "Southern Utah",
    "Miami (Ohio)": "Miami (OH)",
    "Stephen F. Austin State": "Stephen F. Austin",
    "Sam Houston State": "Sam Houston",
    "Houston Christian University": "Houston Christian",
    "Jackson State University": "Jackson State",
    "Fort Valley State College": "Fort Valley State",
    "Albany State (GA)": "Albany State",
    "Texas State-San Marcos": "Texas State",
    "Campbell University": "Campbell",
    "Grand Valley": "Grand Valley State",
    "Cal Poly (San Luis Obispo)": "Cal Poly",
    "Bemidji State University": "Bemidji State",
    "University of Arkansas at Pine Bluff": "Arkansas-Pine Bluff",
    "University of West Florida": "West Florida",
    "Sacred Heart University": "Sacred Heart",
    "Grambling State": "Grambling",
}

# College Scorecard campus coordinates for program locations whose official
# municipality labels are absent from the GeoNames cities500 extract.
COLLEGE_COORDINATE_OVERRIDES = {
    "Penn State": {"place": "University Park", "country": "United States", "lat": 40.7965, "lon": -77.862848},
    "Air Force": {"place": "USAF Academy", "country": "United States", "lat": 39.010957, "lon": -104.891358},
    "Alcorn State": {"place": "Alcorn State", "country": "United States", "lat": 31.877216, "lon": -91.142854},
    "Saginaw Valley State": {"place": "University Center", "country": "United States", "lat": 43.51176, "lon": -83.964273},
}


def split_college_history(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def parse_college_teams(payload: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    aliases: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for wrapper in league.get("teams", []):
                team = wrapper.get("team") or {}
                team_id = str(team.get("id") or "")
                if not team_id:
                    continue
                parsed = {
                    "id": team_id,
                    "name": str(team.get("location") or team.get("displayName") or ""),
                    "display_name": str(team.get("displayName") or team.get("location") or ""),
                }
                for label in (team.get("location"), team.get("abbreviation"), team.get("shortDisplayName"), team.get("displayName")):
                    if label:
                        aliases[normalize(label)][team_id] = parsed
    return {key: list(values.values()) for key, values in aliases.items()}


def match_college_team(college: str, aliases: dict[str, list[dict[str, str]]]) -> tuple[dict[str, str] | None, str]:
    lookup = COLLEGE_ALIASES.get(college, college)
    candidates = aliases.get(normalize(lookup), [])
    if college == "Troy":
        candidates = [team for team in candidates if team["display_name"] == "Troy Trojans"]
    elif college == "Charlotte":
        candidates = [team for team in candidates if team["display_name"] == "Charlotte 49ers"]
    if len(candidates) == 1:
        return candidates[0], "matched"
    return None, "ambiguous college program" if candidates else "college program unavailable"


def parse_home_venue(payload: dict[str, Any], team_id: str) -> dict[str, str] | None:
    venues: Counter[tuple[str, str, str, str]] = Counter()
    for event in payload.get("events", []):
        for competition in event.get("competitions", []):
            competitors = competition.get("competitors", [])
            is_home = any(str(item.get("team", {}).get("id")) == str(team_id) and item.get("homeAway") == "home" for item in competitors)
            venue = competition.get("venue") or {}
            address = venue.get("address") or {}
            if is_home and address.get("city") and address.get("country"):
                venues[(str(address["city"]), str(address.get("state") or ""), str(address["country"]), str(venue.get("fullName") or ""))] += 1
    if not venues:
        return None
    city, state, country, venue = venues.most_common(1)[0][0]
    return {"city": city, "state": state, "country": country, "venue": venue}


def fetch_college_venues(
    colleges: Iterable[str],
    *,
    workers: int = 10,
    force: bool = False,
    teams_cache: Path = DEFAULT_COLLEGE_TEAMS_CACHE,
    venues_cache: Path = DEFAULT_COLLEGE_VENUES_CACHE,
) -> dict[str, dict[str, Any]]:
    client = CachedHttpClient(delay=0.0, timeout=90)
    teams_payload = json.loads(client.fetch_text(ESPN_COLLEGE_TEAMS_URL, teams_cache, force=force).text)
    aliases = parse_college_teams(teams_payload)
    cached: dict[str, dict[str, Any]] = {}
    if venues_cache.exists() and not force:
        try:
            cached = json.loads(venues_cache.read_text(encoding="utf-8")).get("colleges", {})
        except (json.JSONDecodeError, OSError):
            cached = {}
    colleges = sorted({college for college in colleges if college})
    results = {} if force else {
        college: cached[college]
        for college in colleges
        if college in cached and cached[college].get("status") != "venue request failed"
    }
    requests_to_make = []
    for college in colleges:
        if college in results:
            continue
        team, status = match_college_team(college, aliases)
        if not team:
            results[college] = {"status": status}
        else:
            requests_to_make.append((college, team))

    def fetch_one(item: tuple[str, dict[str, str]]) -> tuple[str, dict[str, Any]]:
        college, team = item
        try:
            response = requests.get(ESPN_COLLEGE_SCHEDULE_URL.format(team_id=team["id"]), timeout=30)
            response.raise_for_status()
            venue = parse_home_venue(response.json(), team["id"])
            if not venue:
                return college, {"status": "home venue unavailable", "espn_id": team["id"], "program": team["name"]}
            return college, {"status": "venue found", "espn_id": team["id"], "program": team["name"], **venue}
        except (requests.RequestException, ValueError) as error:
            return college, {"status": "venue request failed", "espn_id": team["id"], "program": team["name"], "error": str(error)}

    if requests_to_make:
        print(f"Fetching {len(requests_to_make):,} college home venues...", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for college, result in executor.map(fetch_one, requests_to_make):
                results[college] = result
    _write_json(venues_cache, {"retrieved_at": datetime.now(timezone.utc).isoformat(), "season": 2025, "colleges": results})
    return results


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
        team_splits = []
        for team_code in team_snaps.index:
            team_rows = rows[rows["team"].eq(team_code)]
            team_splits.append(
                {
                    "team_code": str(team_code),
                    "games": int(team_rows["game_id"].nunique()),
                    "snaps": int(team_rows["total_snaps"].sum()),
                    "offense_snaps": int(team_rows["offense_snaps"].fillna(0).sum()),
                    "defense_snaps": int(team_rows["defense_snaps"].fillna(0).sum()),
                    "special_teams_snaps": int(team_rows["st_snaps"].fillna(0).sum()),
                }
            )
        position = rows["position"].dropna().astype(str).mode()
        names = rows["player"].dropna().astype(str).mode()
        cohort.append(
            {
                "pfr_id": str(player_id),
                "snap_name": names.iloc[0] if len(names) else str(player_id),
                "snap_position": position.iloc[0] if len(position) else None,
                "team_code": str(team_snaps.index[0]),
                "team_codes": [str(team) for team in team_snaps.index],
                "team_splits": team_splits,
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
    # Transient request failures from older builds were once cached as permanent
    # profile results. Keep only successful summaries so a normal build retries
    # anything that failed previously.
    cache = {
        athlete_id: result
        for athlete_id, result in cache.items()
        if isinstance(result, dict) and not result.get("error")
    }
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
                if not result.get("error"):
                    cache[athlete_id] = result
                if index % 100 == 0 or index == len(missing):
                    _write_json(cache_path, cache)
                    print(f"  fetched {index:,}/{len(missing):,}", flush=True)
    return cache


def resolve_college_location(
    venue: dict[str, Any],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
) -> dict[str, Any] | None:
    location = resolve_birthplace(
        {"birth_city": venue.get("city"), "birth_state": venue.get("state"), "birth_country": venue.get("country")},
        city_index,
        country_aliases,
        country_names,
    )
    if location:
        location.update({"venue": venue.get("venue"), "espn_id": venue.get("espn_id"), "program": venue.get("program")})
    return location


def age_on(dob: str | None, on_date: date = date(2026, 2, 8)) -> int | None:
    return _age_on(dob, on_date)


def build_payload(
    snaps: pd.DataFrame,
    players: pd.DataFrame,
    athletes: dict[str, dict[str, Any]],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
    *,
    college_locations: dict[str, dict[str, Any]] | None = None,
    college_statuses: dict[str, str] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    college_locations = college_locations or {}
    college_statuses = college_statuses or {}
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
            else "birth country unavailable" if not athlete.get("birth_country")
            else "birth country unrecognized" if normalize(athlete.get("birth_country")) not in country_aliases
            else "birth city coordinates unavailable"
        )
        team_code = snap["team_code"]
        team, conference, division = TEAM_META[team_code]
        dob = athlete.get("dob") or (str(player.birth_date)[:10] if player is not None and pd.notna(player.birth_date) else None)
        name = str(player.display_name) if player is not None and pd.notna(player.display_name) else snap["snap_name"]
        position = str(player.position) if player is not None and pd.notna(player.position) else snap["snap_position"]
        college_history = split_college_history(player.college_name) if player is not None else []
        college = college_history[0] if college_history else None
        college_location = college_locations.get(college, {}) if college else {}
        college_mapped = bool(college_location)
        college_status = "resolved" if college_mapped else (college_statuses.get(college, "college unavailable") if college else "college unavailable")

        def player_value(field: str) -> Any:
            value = getattr(player, field, None) if player is not None else None
            return None if value is None or pd.isna(value) else value

        def player_int(field: str) -> int | None:
            value = player_value(field)
            return int(float(value)) if value is not None else None
        record = {
            "id": f"nfl:{snap['pfr_id']}",
            "pfrId": snap["pfr_id"],
            "espnId": espn_id,
            "name": name,
            "team": team,
            "teamCode": team_code,
            "teams": [TEAM_META[code][0] for code in snap["team_codes"] if code in TEAM_META],
            "teamSplits": [
                {
                    "team": TEAM_META[split["team_code"]][0],
                    "teamCode": split["team_code"],
                    "conference": TEAM_META[split["team_code"]][1],
                    "division": TEAM_META[split["team_code"]][2],
                    "games": split["games"],
                    "snaps": split["snaps"],
                    "offenseSnaps": split["offense_snaps"],
                    "defenseSnaps": split["defense_snaps"],
                    "specialTeamsSnaps": split["special_teams_snaps"],
                }
                for split in snap["team_splits"]
                if split["team_code"] in TEAM_META
            ],
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
            "collegeHistory": college_history,
            "collegeConference": player_value("college_conference"),
            "collegePlace": college_location.get("place"),
            "collegeCountry": college_location.get("country"),
            "collegeLat": college_location.get("lat"),
            "collegeLon": college_location.get("lon"),
            "collegeMapped": college_mapped,
            "collegeStatus": college_status,
            "collegeEspnId": college_location.get("espn_id"),
            "collegeVenue": college_location.get("venue"),
            "draftYear": player_int("draft_year"),
            "draftRound": player_int("draft_round"),
            "draftPick": player_int("draft_pick"),
            "draftTeam": player_value("draft_team"),
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
    college_records = [record for record in records if record["college"]]
    college_mapped_records = [record for record in college_records if record["collegeMapped"]]
    total_snaps = sum(record["snaps"] for record in records)
    mapped_snaps = sum(record["snaps"] for record in mapped_records)
    college_snaps = sum(record["snaps"] for record in college_records)
    college_mapped_snaps = sum(record["snaps"] for record in college_mapped_records)
    unresolved_colleges = []
    for college in sorted({record["college"] for record in college_records if not record["collegeMapped"]}):
        rows = [record for record in college_records if record["college"] == college]
        unresolved_colleges.append({"college": college, "players": len(rows), "snaps": sum(row["snaps"] for row in rows), "status": rows[0]["collegeStatus"]})
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
            "college_source_name": "nflverse player records",
            "college_location_source_name": "ESPN college football home venues + GeoNames",
            "college_coordinate_override_source_name": "U.S. Department of Education College Scorecard",
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
            "college_players": len(college_records),
            "college_mapped_players": len(college_mapped_records),
            "college_player_coverage_pct": round(len(college_mapped_records) / len(college_records) * 100, 1) if college_records else 0,
            "college_snaps": college_snaps,
            "college_mapped_snaps": college_mapped_snaps,
            "college_snap_coverage_pct": round(college_mapped_snaps / college_snaps * 100, 1) if college_snaps else 0,
            "colleges": len({record["college"] for record in college_records}),
            "mapped_colleges": len({record["college"] for record in college_mapped_records}),
            "college_countries": len({record["collegeCountry"] for record in college_mapped_records}),
            "unresolved_colleges": len(unresolved_colleges),
        },
        "records": records,
        "unresolved": unresolved,
        "college_unresolved": unresolved_colleges,
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
    college_rows = players[players["pfr_id"].astype(str).isin(player_ids)]
    primary_colleges = {
        history[0]
        for value in college_rows["college_name"].tolist()
        if (history := split_college_history(value))
    }
    college_venues = fetch_college_venues(primary_colleges, workers=workers, force=force)
    needed_names = {normalize(row.get("birth_city")) for row in athletes.values() if row.get("birth_city")}
    needed_names.update(normalize(row.get("city")) for row in college_venues.values() if row.get("city"))
    cities_path = geonames_input or _download_binary(GEONAMES_CITIES_URL, DEFAULT_GEONAMES_CACHE, force=force)
    countries_path = countries_input
    if countries_path is None:
        CachedHttpClient(delay=0.0, timeout=90).fetch_text(
            GEONAMES_COUNTRIES_URL, DEFAULT_COUNTRIES_CACHE, force=force
        )
        countries_path = DEFAULT_COUNTRIES_CACHE
    country_aliases, country_names = load_country_codes(countries_path)
    city_index = build_city_index(cities_path, needed_names)
    college_locations = {}
    college_statuses = {}
    for college, venue in college_venues.items():
        resolved = resolve_college_location(venue, city_index, country_aliases, country_names)
        if not resolved and college in COLLEGE_COORDINATE_OVERRIDES:
            resolved = {**COLLEGE_COORDINATE_OVERRIDES[college], "geonames_id": None, "venue": venue.get("venue"), "espn_id": venue.get("espn_id"), "program": venue.get("program")}
        if resolved:
            college_locations[college] = resolved
        else:
            college_statuses[college] = venue.get("status", "college coordinates unavailable") if not venue.get("city") else "college coordinates unavailable"
    payload = build_payload(
        snaps,
        players,
        athletes,
        city_index,
        country_aliases,
        country_names,
        college_locations=college_locations,
        college_statuses=college_statuses,
    )
    _write_json(output_path, payload)
    print(
        f"Wrote {payload['summary']['players']:,} NFL players with "
        f"{payload['summary']['player_coverage_pct']:.1f}% birthplace coverage to {output_path}"
    )
    print(f"College coverage: {payload['summary']['college_player_coverage_pct']:.1f}% of players with a listed college")
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
