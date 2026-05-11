from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from reaviz_bot.constants import CHOOSE_COUNT_BUTTON, START_BUTTON, STOP_TEST_BUTTON
from reaviz_bot.evaluator import AnswerEvaluator
from reaviz_bot.keyboards import KeyboardFactory
from reaviz_bot.message_formatter import QuestionMessageFormatter
from reaviz_bot.models import TestSession
from reaviz_bot.question_bank import QuestionBank
from reaviz_bot.session_store import TelegramSessionStore
from reaviz_bot.text_utils import normalize_spaces


class TelegramBotHandlers:
    def __init__(
        self,
        question_bank: QuestionBank,
        keyboards: KeyboardFactory | None = None,
        formatter: QuestionMessageFormatter | None = None,
        evaluator: AnswerEvaluator | None = None,
        sessions: TelegramSessionStore | None = None,
    ) -> None:
        self.question_bank = question_bank
        self.keyboards = keyboards or KeyboardFactory()
        self.formatter = formatter or QuestionMessageFormatter()
        self.evaluator = evaluator or AnswerEvaluator()
        self.sessions = sessions or TelegramSessionStore()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.reset(context)
        await update.message.reply_text(
            "Привет! Я помогу прорешивать тесты по анатомии.",
            reply_markup=self.keyboards.main_menu(),
        )

    async def start_test_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.set(context, TestSession(questions=[], awaiting_count=False))
        await self._show_test_menu(
            update,
            "Выберите действие: укажите количество вопросов для теста или остановите текущий тест.",
        )

    async def ask_for_question_count(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        session = self.sessions.get(context)
        if session is None:
            session = TestSession(questions=[], awaiting_count=True)
            self.sessions.set(context, session)
        session.awaiting_count = True

        await update.message.reply_text(
            f"Введите количество вопросов от 1 до {self.question_bank.total_questions}.",
            reply_markup=self.keyboards.test_menu(),
        )

    async def stop_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        self.sessions.reset(context)
        await update.message.reply_text(
            "Тест остановлен. Когда захотите продолжить, нажмите «Начать тест».",
            reply_markup=self.keyboards.main_menu(),
        )

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        text = normalize_spaces(update.message.text)

        if text == START_BUTTON:
            await self.start_test_menu(update, context)
            return
        if text == CHOOSE_COUNT_BUTTON:
            await self.ask_for_question_count(update, context)
            return
        if text == STOP_TEST_BUTTON:
            await self.stop_test(update, context)
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

        text = normalize_spaces(update.message.text)
        if not text.isdigit():
            await update.message.reply_text("Введите число, например: 20")
            return

        count = int(text)
        if not 1 <= count <= self.question_bank.total_questions:
            await update.message.reply_text(f"Введите число от 1 до {self.question_bank.total_questions}.")
            return

        await self.start_random_test(update, context, count)

    async def start_random_test(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        count: int,
    ) -> None:
        session = TestSession(questions=self.question_bank.pick_random(count))
        self.sessions.set(context, session)

        await update.message.reply_text(
            f"Отлично, начинаем тест из {count} вопросов.",
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

