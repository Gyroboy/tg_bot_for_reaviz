from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from reaviz_bot.constants import ANATOMY_SUBJECT, HISTOLOGY_SUBJECT


ENV_FILE = Path(".env")
def default_question_files() -> "dict[str, Path]":
    return {
        ANATOMY_SUBJECT: Path("anatomy_test.xlsx"),
        HISTOLOGY_SUBJECT: Path("histology_test.xlsx"),
    }


QUESTION_FILES = default_question_files()


@dataclass(frozen=True, slots=True)
class BotConfig:
    token: str
    question_files: "dict[str, Path]" = field(default_factory=default_question_files)

    @classmethod
    def from_environment(cls) -> "BotConfig":
        load_dotenv(ENV_FILE)

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "Не найден TELEGRAM_BOT_TOKEN. Создайте файл .env рядом с bot.py "
                "и добавьте строку TELEGRAM_BOT_TOKEN=ваш_токен"
            )

        return cls(token=token)
