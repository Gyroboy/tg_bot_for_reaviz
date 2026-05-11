from __future__ import annotations

import re


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def strip_option_prefix(text: str) -> str:
    return normalize_spaces(re.sub(r"^\s*[а-яa-z]\)\s*", "", text, flags=re.IGNORECASE))

