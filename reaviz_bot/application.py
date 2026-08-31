from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from reaviz_bot.config import BotConfig
from reaviz_bot.handlers import TelegramBotHandlers
from reaviz_bot.question_bank import QuestionBank
from reaviz_bot.question_repository import ExcelQuestionRepository


LOGGER = logging.getLogger(__name__)


class BotApplicationFactory:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def build(self) -> Application:
        question_banks: dict[str, QuestionBank] = {}
        for subject, path in self.config.question_files.items():
            questions = ExcelQuestionRepository(path).load_questions()
            if not questions:
                raise RuntimeError(f"Не удалось загрузить вопросы из файла {path}.")
            question_banks[subject] = QuestionBank(questions)

        handlers = TelegramBotHandlers(question_banks)

        application = Application.builder().token(self.config.token).build()
        application.bot_data["total_questions"] = {
            subject: bank.total_questions for subject, bank in question_banks.items()
        }
        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CallbackQueryHandler(handlers.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
        LOGGER.info("Loaded questions: %s", application.bot_data["total_questions"])
        return application


def build_application() -> Application:
    return BotApplicationFactory(BotConfig.from_environment()).build()

