from __future__ import annotations

import random

from reaviz_bot.models import Question


class QuestionBank:
    def __init__(self, questions: list[Question]) -> None:
        if not questions:
            raise ValueError("Question bank cannot be empty.")
        self._questions = questions
        self._questions_by_id = {question.question_id: question for question in questions}

    @property
    def total_questions(self) -> int:
        return len(self._questions)

    def pick_random(self, count: int) -> list[Question]:
        return random.sample(self._questions, count)

    def pick_by_numbers(self, numbers: list[int]) -> list[Question]:
        return [self._questions_by_id[number] for number in numbers if number in self._questions_by_id]
