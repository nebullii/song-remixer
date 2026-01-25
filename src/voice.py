"""Voice selection helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path


DEFAULT_GENDER = "neutral"

# Small heuristic lists for first-name detection (best-effort only).
FEMALE_FIRST_NAMES = {
    "adele", "alicia", "amy", "anna", "ariana", "beyonce", "billie", "carly",
    "celine", "christina", "dua", "ellie", "fiona", "gwen", "halsey", "janet",
    "jessie", "joan", "joni", "katy", "kelly", "lady", "lana", "laura",
    "lorde", "madonna", "mariah", "norah", "olivia", "pink", "rihanna",
    "selena", "sia", "stevie", "sza", "taylor", "whitney", "zara",
}

MALE_FIRST_NAMES = {
    "bruno", "chris", "drake", "ed", "elton", "eminem", "frank", "harry",
    "jack", "james", "jason", "jay", "john", "justin", "kanye", "kendrick",
    "kurt", "lil", "michael", "nick", "paul", "post", "sam", "the", "tyler",
    "weeknd", "zayn",
}


def _normalize_artist(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", name.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_gender_hint(hint: str | None) -> str | None:
    if not hint:
        return None
    token = re.sub(r"[^a-z]", "", hint.lower())
    if token in {"female", "woman", "girl"}:
        return "female"
    if token in {"male", "man", "boy"}:
        return "male"
    if token in {"neutral", "androgynous"}:
        return "neutral"
    return None


def _load_artist_gender_map() -> dict[str, str]:
    root = Path(__file__).resolve().parent.parent
    data_path = root / "data" / "artist_gender.json"
    if not data_path.exists():
        return {}
    try:
        with data_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k).lower(): str(v).lower() for k, v in raw.items()}


def guess_vocal_gender(artist: str, hint: str | None = None) -> str:
    """Best-effort gender guess; prefer explicit hint or local mapping."""
    normalized_hint = _normalize_gender_hint(hint)
    if normalized_hint:
        return normalized_hint

    artist_map = _load_artist_gender_map()
    normalized_artist = _normalize_artist(artist)
    mapped = artist_map.get(normalized_artist)
    if mapped in {"female", "male", "neutral"}:
        return mapped

    # Heuristic: avoid guessing for bands/groups.
    if re.search(r"\b(and|&|feat|featuring)\b", normalized_artist):
        return DEFAULT_GENDER

    first = normalized_artist.split(" ", 1)[0] if normalized_artist else ""
    if first in FEMALE_FIRST_NAMES:
        return "female"
    if first in MALE_FIRST_NAMES:
        return "male"

    return DEFAULT_GENDER
