"""Shared GeoNames inputs and existing country/state matching policies."""
from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from .utils import normalize_key as normalize

ROOT = Path(__file__).resolve().parents[2]
GEONAMES_CITIES_URL = "https://download.geonames.org/export/dump/cities500.zip"
GEONAMES_COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
DEFAULT_GEONAMES_CACHE = ROOT / "data" / "cache" / "cities500.zip"
DEFAULT_COUNTRIES_CACHE = ROOT / "data" / "cache" / "geonames_country_info.txt"
DEFAULT_ADMIN1_CACHE = ROOT / "data" / "cache" / "geonames_admin1_codes.txt"


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
    if not country_code:
        return None
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


def load_admin1_aliases(path: Path) -> dict[tuple[str, str], str]:
    aliases: dict[tuple[str, str], str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 3 or "." not in fields[0]:
            continue
        country_code, admin_code = fields[0].split(".", 1)
        for value in (admin_code, fields[1], fields[2]):
            if value:
                aliases[(country_code, normalize(value))] = admin_code
    return aliases


def resolve_birthplace_with_admin1(
    profile: dict[str, Any],
    city_index: dict[str, list[dict[str, Any]]],
    country_aliases: dict[str, str],
    country_names: dict[str, str],
    admin1_aliases: dict[tuple[str, str], str],
) -> dict[str, Any] | None:
    city = profile.get("birth_city")
    country_code = country_aliases.get(normalize(profile.get("birth_country")))
    if not city or not country_code:
        return None
    candidates = [
        candidate for candidate in city_index.get(normalize(city), [])
        if candidate["country_code"] == country_code
    ]
    state = normalize(profile.get("birth_state"))
    admin_code = admin1_aliases.get((country_code, state)) if state else None
    if admin_code:
        candidates = [candidate for candidate in candidates if candidate["admin1"] == admin_code]
    if not candidates:
        return None
    match = max(candidates, key=lambda candidate: candidate["population"])
    return {
        "place": str(city),
        "country": country_names.get(country_code, str(profile.get("birth_country") or country_code)),
        "lat": round(float(match["lat"]), 6),
        "lon": round(float(match["lon"]), 6),
        "geonames_id": str(match["geonames_id"]),
    }
