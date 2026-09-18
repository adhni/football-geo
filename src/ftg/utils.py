"""Shared file and value helpers; sport-specific policy stays in each builder."""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import requests


def write_json(path: Path, value: Any, *, pretty: bool = False) -> None:
    """Replace a JSON file only after serialization and writing succeed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    options = {"ensure_ascii": False, "indent": 2, "sort_keys": True} if pretty else {
        "ensure_ascii": False, "separators": (",", ":")
    }
    temporary.write_text(json.dumps(value, **options), encoding="utf-8")
    temporary.replace(path)


def download_binary(url: str, path: Path, *, force: bool = False) -> Path:
    """Reuse a cached download, replacing it only after a successful response."""
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


def normalize_key(value: object) -> str:
    """Return the existing ASCII lookup key, without extra transliteration rules."""
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def age_on(dob: str | None, on_date: date) -> int | None:
    """Age at an explicit snapshot date; missing or invalid ISO dates stay unknown."""
    if not dob:
        return None
    try:
        born = date.fromisoformat(dob[:10])
    except ValueError:
        return None
    return on_date.year - born.year - ((on_date.month, on_date.day) < (born.month, born.day))
