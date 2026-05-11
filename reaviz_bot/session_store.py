from __future__ import annotations

from telegram.ext import ContextTypes

from reaviz_bot.models import TestSession


class TelegramSessionStore:
    _SESSION_KEY = "session"

    def get(self, context: ContextTypes.DEFAULT_TYPE) -> TestSession | None:
        return context.chat_data.get(self._SESSION_KEY)

    def set(self, context: ContextTypes.DEFAULT_TYPE, session: TestSession | None) -> None:
        context.chat_data[self._SESSION_KEY] = session

    def reset(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.set(context, None)

