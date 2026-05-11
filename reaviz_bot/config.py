from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(".env")
QUESTION_FILE = Path("anatomy_test.xlsx")


@dataclass(frozen=True, slots=True)
class BotConfig:
    token: str
    question_file: Path = QUESTION_FILE

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
