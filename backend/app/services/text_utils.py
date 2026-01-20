from __future__ import annotations

import re

_NAME_PATTERN = re.compile(r"\b[A-Z][a-z]{1,20}\b")
_STOPWORDS = {
    "I",
    "We",
    "The",
    "A",
    "An",
    "And",
    "But",
    "So",
    "OK",
    "Okay",
    "Thanks",
    "Today",
    "Meeting",
    "Agenda",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "meeting"


def extract_candidate_names(text: str) -> list[str]:
    matches = _NAME_PATTERN.findall(text)
    names = [match for match in matches if match not in _STOPWORDS]
    return list(dict.fromkeys(names))
