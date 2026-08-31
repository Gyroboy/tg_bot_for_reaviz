from __future__ import annotations

import re

from telegram import Update
from telegram.ext import ContextTypes

from reaviz_bot.constants import (
    BACK_BUTTON,
    CHANGE_SUBJECT_BUTTON,
    CHOOSE_COUNT_BUTTON,
    CHOOSE_NUMBERS_BUTTON,
    START_BUTTON,
    STOP_TEST_BUTTON,
    SUBJECT_BUTTONS,
    SUBJECT_NAMES,
    SUBJECT_NAMES_GENITIVE,
)
from reaviz_bot.evaluator import AnswerEvaluator
from reaviz_bot.keyboards import KeyboardFactory
from reaviz_bot.message_formatter import QuestionMessageFormatter
from reaviz_bot.models import Question, TestSession
from reaviz_bot.question_bank import QuestionBank
from reaviz_bot.session_store import TelegramSessionStore
from reaviz_bot.text_utils import normalize_spaces


class TelegramBotHandlers:
    def __init__(
        self,
        question_banks: dict[str, QuestionBank],
        keyboards: KeyboardFactory | None = None,
        formatter: QuestionMessageFormatter | None = None,
        evaluator: AnswerEvaluator | None = None,
        sessions: TelegramSessionStore | None = None,
    ) -> None:
        self.question_banks = question_banks
        self.keyboards = keyboards or KeyboardFactory()
        self.formatter = formatter or QuestionMessageFormatter()
        self.evaluator = evaluator or AnswerEvaluator()
        self.sessions = sessions or TelegramSessionStore()

    def _bank_for(self, context: ContextTypes.DEFAULT_TYPE) -> QuestionBank | None:
        subject = self.sessions.get_subject(context)
        if subject is None:
            return None
        return self.question_banks.get(subject)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.reset(context)
        self.sessions.set_subject(context, None)
        await update.message.reply_text(
            "Привет! Я помогу прорешивать тесты. Выберите предмет:",
            reply_markup=self.keyboards.subject_menu(),
        )

    async def choose_subject(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        subject: str,
    ) -> None:
        self.sessions.reset(context)
        self.sessions.set_subject(context, subject)
        bank = self.question_banks[subject]
        await update.message.reply_text(
            f"Предмет: {SUBJECT_NAMES[subject]}. Вопросов в базе: {bank.total_questions}.\n"
            "Нажмите «Начать тест».",
            reply_markup=self.keyboards.main_menu(),
        )

    async def prompt_for_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Сначала выберите предмет.",
            reply_markup=self.keyboards.subject_menu(),
        )

    async def start_test_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.set(context, TestSession(questions=[]))
        subject = self.sessions.get_subject(context)
        await self._show_test_menu(
            update,
            f"Тест по {SUBJECT_NAMES_GENITIVE[subject]}. "
            "Выберите действие: случайные вопросы, вопросы по номерам или остановка текущего теста.",
        )

    async def ask_for_question_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        bank = self._bank_for(context)
        if bank is None:
            await self.prompt_for_subject(update, context)
            return

        session = self.sessions.get(context)
        if session is None:
            session = TestSession(questions=[], awaiting_count=True)
            self.sessions.set(context, session)
        session.awaiting_count = True
        session.awaiting_numbers = False

        await update.message.reply_text(
            f"Введите количество вопросов от 1 до {bank.total_questions}.",
            reply_markup=self.keyboards.test_menu(),
        )

    async def ask_for_question_numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            session = TestSession(questions=[], awaiting_numbers=True)
            self.sessions.set(context, session)
        session.awaiting_count = False
        session.awaiting_numbers = True

        await update.message.reply_text(
            "Введите номера вопросов, например: 10-15. Можно также указать несколько номеров через запятую.",
            reply_markup=self.keyboards.test_menu(),
        )

    async def stop_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.reset(context)
        await update.message.reply_text(
            "Тест остановлен. Когда захотите продолжить, нажмите «Начать тест».",
            reply_markup=self.keyboards.main_menu(),
        )

    async def go_back(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)

        # Из ввода количества/номеров — возвращаемся в меню теста, а не дальше.
        if session is not None and (session.awaiting_count or session.awaiting_numbers):
            session.awaiting_count = False
            session.awaiting_numbers = False
            await update.message.reply_text(
                "Ок, вернулись в меню теста.",
                reply_markup=self.keyboards.test_menu(),
            )
            return

        # Из меню теста или во время теста — в меню предмета.
        self.sessions.reset(context)
        subject = self.sessions.get_subject(context)
        await update.message.reply_text(
            f"Меню предмета «{SUBJECT_NAMES[subject]}». "
            "Нажмите «Начать тест» или смените предмет.",
            reply_markup=self.keyboards.main_menu(),
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = normalize_spaces(update.message.text)

        if text in SUBJECT_BUTTONS:
            await self.choose_subject(update, context, SUBJECT_BUTTONS[text])
            return
        if text == CHANGE_SUBJECT_BUTTON:
            await self.start(update, context)
            return

        if self.sessions.get_subject(context) is None:
            await self.prompt_for_subject(update, context)
            return

        if text == START_BUTTON:
            await self.start_test_menu(update, context)
            return
        if text == CHOOSE_COUNT_BUTTON:
            await self.ask_for_question_count(update, context)
            return
        if text == CHOOSE_NUMBERS_BUTTON:
            await self.ask_for_question_numbers(update, context)
            return
        if text == STOP_TEST_BUTTON:
            await self.stop_test(update, context)
            return
        if text == BACK_BUTTON:
            await self.go_back(update, context)
            return

        await self.handle_test_input(update, context)

    async def handle_test_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is not None and session.awaiting_numbers:
            await self.handle_numbers_input(update, context)
            return

        await self.handle_count_input(update, context)

    async def handle_count_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None or not session.awaiting_count:
            await update.message.reply_text(
                "Нажмите «Начать тест», чтобы открыть меню.",
                reply_markup=self.keyboards.main_menu(),
            )
            return

        bank = self._bank_for(context)
        if bank is None:
            await self.prompt_for_subject(update, context)
            return

        text = normalize_spaces(update.message.text)
        if not text.isdigit():
            await update.message.reply_text("Введите число, например: 20")
            return

        count = int(text)
        if not 1 <= count <= bank.total_questions:
            await update.message.reply_text(f"Введите число от 1 до {bank.total_questions}.")
            return

        await self.start_random_test(update, context, count)

    async def handle_numbers_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None or not session.awaiting_numbers:
            await update.message.reply_text(
                "Нажмите «Начать тест», чтобы открыть меню.",
                reply_markup=self.keyboards.main_menu(),
            )
            return

        bank = self._bank_for(context)
        if bank is None:
            await self.prompt_for_subject(update, context)
            return

        text = normalize_spaces(update.message.text)
        numbers = self._parse_question_numbers(text)
        if not numbers:
            await update.message.reply_text("Введите номера вопросов, например: 10-15 или 10, 12, 15.")
            return

        questions = bank.pick_by_numbers(numbers)
        if not questions:
            await update.message.reply_text("Не нашёл вопросов с такими номерами. Проверьте ввод и попробуйте ещё раз.")
            return

        found_numbers = {question.question_id for question in questions}
        missing_numbers = [number for number in numbers if number not in found_numbers]
        if missing_numbers:
            missing_text = ", ".join(str(number) for number in missing_numbers[:10])
            suffix = "..." if len(missing_numbers) > 10 else ""
            await update.message.reply_text(
                f"Некоторые номера не найдены: {missing_text}{suffix}. Начинаю тест по найденным вопросам."
            )

        await self.start_selected_test(update, context, questions)

    async def start_random_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        count: int,
    ) -> None:
        bank = self._bank_for(context)
        if bank is None:
            await self.prompt_for_subject(update, context)
            return

        session = TestSession(questions=bank.pick_random(count))
        self.sessions.set(context, session)

        await update.message.reply_text(
            f"Отлично, начинаем тест из {count} вопросов.",
            reply_markup=self.keyboards.test_menu(),
        )
        await self.send_current_question(update.effective_chat.id, context)

    async def start_selected_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        questions: list[Question],
    ) -> None:
        session = TestSession(questions=questions)
        self.sessions.set(context, session)

        await update.message.reply_text(
            f"Отлично, начинаем тест по выбранным вопросам: {len(questions)} шт.",
            reply_markup=self.keyboards.test_menu(),
        )
        await self.send_current_question(update.effective_chat.id, context)

    async def send_current_question(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None or session.current_index >= session.total_questions:
            return

        question = session.current_question
        if question.is_matching:
            keyboard = self.keyboards.matching(question, session.selected_indexes, session.matching_step)
        elif question.has_multiple_answers:
            keyboard = self.keyboards.multiple_choice(question, session.selected_indexes)
        else:
            keyboard = self.keyboards.single_choice(question)

        await context.bot.send_message(
            chat_id=chat_id,
            text=self.formatter.format_question(session),
            reply_markup=keyboard,
        )

    async def finish_test(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            return

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"Тест завершён.\n"
                f"Правильных ответов: {session.correct_answers} из {session.total_questions}."
            ),
            reply_markup=self.keyboards.test_menu(),
        )
        session.awaiting_count = False
        session.awaiting_numbers = False

    async def move_to_next_question(self, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            return

        session.move_next()
        if session.current_index >= session.total_questions:
            await self.finish_test(chat_id, context)
            return

        await self.send_current_question(chat_id, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        data = query.data or ""

        if data.startswith("answer:"):
            await self.handle_single_answer(query, context, int(data.split(":", 1)[1]))
            return
        if data.startswith("toggle:"):
            await self.handle_multiple_answer_toggle(query, context, int(data.split(":", 1)[1]))
            return
        if data.startswith("match_toggle:"):
            await self.handle_matching_toggle(query, context, int(data.split(":", 1)[1]))
            return
        if data == "match_next":
            await self.handle_matching_next(query, context)
            return
        if data == "submit":
            await self.handle_multiple_answer_submit(query, context)

    async def handle_single_answer(self, query, context: ContextTypes.DEFAULT_TYPE, option_index: int) -> None:
        session = self.sessions.get(context)
        if session is None:
            await query.answer("Сначала начните тест.")
            return

        question = session.current_question
        is_correct, response_text = self.evaluator.evaluate_choice(question, {option_index})
        if is_correct:
            session.mark_correct()

        await query.answer()
        await query.message.reply_text(response_text)
        await self.move_to_next_question(query.message.chat_id, context)

    async def handle_multiple_answer_toggle(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        option_index: int,
    ) -> None:
        session = self.sessions.get(context)
        if session is None:
            await query.answer("Сначала начните тест.")
            return

        session.toggle_selected_index(option_index)
        await query.answer("Ответ обновлён")
        await query.edit_message_reply_markup(
            reply_markup=self.keyboards.multiple_choice(session.current_question, session.selected_indexes)
        )

    async def handle_multiple_answer_submit(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            await query.answer("Сначала начните тест.")
            return

        if not session.selected_indexes:
            await query.answer("Сначала выберите хотя бы один вариант.")
            return

        is_correct, response_text = self.evaluator.evaluate_choice(
            session.current_question,
            session.selected_indexes,
        )
        if is_correct:
            session.mark_correct()

        await query.answer()
        await query.message.reply_text(response_text)
        await self.move_to_next_question(query.message.chat_id, context)

    async def handle_matching_toggle(self, query, context: ContextTypes.DEFAULT_TYPE, option_index: int) -> None:
        session = self.sessions.get(context)
        if session is None:
            await query.answer("Сначала начните тест.")
            return

        session.toggle_selected_index(option_index)
        await query.answer("Выбор обновлён")
        await query.edit_message_reply_markup(
            reply_markup=self.keyboards.matching(
                session.current_question,
                session.selected_indexes,
                session.matching_step,
            )
        )

    async def handle_matching_next(self, query, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            await query.answer("Сначала начните тест.")
            return

        if not session.selected_indexes:
            await query.answer("Сначала выберите хотя бы один вариант.")
            return

        question = session.current_question
        session.save_matching_step()

        if session.matching_step >= len(question.matching_labels):
            is_correct, response_text = self.evaluator.evaluate_matching(question, session.matching_answers)
            if is_correct:
                session.mark_correct()
            await query.answer()
            await query.message.reply_text(response_text)
            await self.move_to_next_question(query.message.chat_id, context)
            return

        await query.answer("Переходим к следующему пункту")
        await query.message.reply_text(
            f"Теперь выберите вариант(ы) для пункта {question.matching_labels[session.matching_step]}.",
            reply_markup=self.keyboards.matching(question, session.selected_indexes, session.matching_step),
        )

    async def _show_test_menu(self, update: Update, text: str) -> None:
        if update.message:
            await update.message.reply_text(text, reply_markup=self.keyboards.test_menu())

    def _parse_question_numbers(self, text: str) -> list[int]:
        if not re.fullmatch(r"\d+(?:\s*-\s*\d+)?(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*", text):
            return []

        numbers: list[int] = []
        seen: set[int] = set()
        for part in text.split(","):
            bounds = [int(value.strip()) for value in part.split("-", 1)]
            start = bounds[0]
            end = bounds[-1]
            if start > end:
                start, end = end, start
            for number in range(start, end + 1):
                if number not in seen:
                    numbers.append(number)
                    seen.add(number)
        return numbers
