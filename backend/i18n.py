import os
from typing import Dict


def get_language() -> str:
    value = (
        os.getenv("APP_LANGUAGE")
        or os.getenv("MEETING_LANGUAGE")
        or os.getenv("LANGUAGE")
        or "ko"
    )
    value = value.lower()
    if value.startswith("en"):
        return "en"
    return "ko"


def is_english() -> bool:
    return get_language() == "en"


def pick(ko: str, en: str) -> str:
    return en if is_english() else ko


def default_stt_language() -> str:
    return "en" if is_english() else "ko"


LABELS: Dict[str, Dict[str, str]] = {
    "title": {"ko": "- **제목**:", "en": "- **Title**:"},
    "datetime": {"ko": "- **일시**:", "en": "- **Date/Time**:"},
    "participants": {"ko": "## 참석자", "en": "## Participants"},
    "agenda": {"ko": "## 아젠다", "en": "## Agenda"},
    "intervention_type": {"ko": "- **유형**:", "en": "- **Type**:"},
    "intervention_message": {"ko": "- **메시지**:", "en": "- **Message**:"},
    "violated_principle": {"ko": "- **위반 원칙**:", "en": "- **Violated principle**:"},
}


def label(key: str) -> str:
    value = LABELS.get(key, {})
    return value.get(get_language(), "")


def label_variants(key: str) -> list[str]:
    value = LABELS.get(key, {})
    return [item for item in value.values() if item]
