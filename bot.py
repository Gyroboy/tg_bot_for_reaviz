from __future__ import annotations

import logging

from reaviz_bot.application import build_application


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    application = build_application()
    LOGGER.info("Бот загружен. Вопросов: %s", application.bot_data["total_questions"])
    application.run_polling()


if __name__ == "__main__":
    main()
