from __future__ import annotations

from reaviz_bot.models import Question


class AnswerEvaluator:
    def evaluate_choice(self, question: Question, selected_indexes: set[int]) -> tuple[bool, str]:
        correct_set = set(question.correct_indexes)
        is_correct = selected_indexes == correct_set
        correct_text = question.correct_option_text()

        if is_correct:
            return True, f"✅ Верно!\n\nПравильный ответ:\n{correct_text}"
        return False, f"❌ Неверно.\n\nПравильный ответ:\n{correct_text}"

    def evaluate_matching(self, question: Question, selected_groups: list[list[int]]) -> tuple[bool, str]:
        normalized_selected = [sorted(group) for group in selected_groups]
        normalized_expected = [sorted(group) for group in question.matching_groups]
        is_correct = normalized_selected == normalized_expected
        correct_text = question.correct_option_text()

        if is_correct:
            return True, (
                "✅ Верно! Соответствие указано правильно."
                f"\n\nПравильный ответ:\n{correct_text}"
            )
        return False, f"❌ Неверно.\n\nПравильное соответствие:\n{correct_text}"

