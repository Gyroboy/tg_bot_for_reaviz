from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from reaviz_bot.constants import (
    CHOOSE_COUNT_BUTTON,
    CHOOSE_NUMBERS_BUTTON,
    OPTION_LETTERS,
    START_BUTTON,
    STOP_TEST_BUTTON,
)
from reaviz_bot.models import Question


class KeyboardFactory:
    def main_menu(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup([[START_BUTTON]], resize_keyboard=True)

    def test_menu(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            [[CHOOSE_COUNT_BUTTON], [CHOOSE_NUMBERS_BUTTON], [STOP_TEST_BUTTON]],
            resize_keyboard=True,
        )

    def single_choice(self, question: Question) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(OPTION_LETTERS[index], callback_data=f"answer:{index}")]
            for index in range(len(question.options))
        ]
        return InlineKeyboardMarkup(buttons)

    def multiple_choice(self, question: Question, selected: set[int]) -> InlineKeyboardMarkup:
        buttons = []
        for index in range(len(question.options)):
            letter = OPTION_LETTERS[index]
            mark = "☑" if index in selected else "☐"
            buttons.append([InlineKeyboardButton(f"{mark} {letter}", callback_data=f"toggle:{index}")])
        buttons.append([InlineKeyboardButton("✅ Ответить", callback_data="submit")])
        return InlineKeyboardMarkup(buttons)

    def matching(self, question: Question, selected: set[int], step: int) -> InlineKeyboardMarkup:
        buttons = []
        for index in range(len(question.options)):
            mark = "☑" if index in selected else "☐"
            buttons.append([InlineKeyboardButton(f"{mark} {index + 1}", callback_data=f"match_toggle:{index}")])

        current_label = question.matching_labels[step]
        buttons.append(
            [InlineKeyboardButton(f"✅ Готово для пункта {current_label}", callback_data="match_next")]
        )
        return InlineKeyboardMarkup(buttons)
