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
        questions = ExcelQuestionRepository(self.config.question_file).load_questions()
        if not questions:
            raise RuntimeError(f"Не удалось загрузить вопросы из файла {self.config.question_file}.")

        question_bank = QuestionBank(questions)
        handlers = TelegramBotHandlers(question_bank)

        application = Application.builder().token(self.config.token).build()
        application.bot_data["total_questions"] = question_bank.total_questions
        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CallbackQueryHandler(handlers.handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
        LOGGER.info("Loaded questions: %s", question_bank.total_questions)
        return application


def build_application() -> Application:
    return BotApplicationFactory(BotConfig.from_environment()).build()

