from __future__ import annotations

from dataclasses import dataclass, field

from reaviz_bot.constants import OPTION_LETTERS


@dataclass(slots=True)
class Question:
    question_id: int
    text: str
    options: list[str]
    correct_indexes: list[int]
    question_type: str
    matching_groups: list[list[int]] = field(default_factory=list)
    matching_labels: list[str] = field(default_factory=list)

    @property
    def has_multiple_answers(self) -> bool:
        return self.question_type == "multi"

    @property
    def is_matching(self) -> bool:
        return self.question_type == "matching"

    def correct_option_text(self) -> str:
        if self.is_matching:
            parts = []
            for label, group in zip(self.matching_labels, self.matching_groups):
                mapped = ", ".join(str(index + 1) for index in group)
                parts.append(f"{label}) {mapped}")
            return "\n".join(parts)

        lines = []
        for index in self.correct_indexes:
            letter = OPTION_LETTERS[index]
            lines.append(f"{letter}) {self.options[index]}")
        return "\n".join(lines)


@dataclass(slots=True)
class TestSession:
    questions: list[Question]
    awaiting_count: bool = False
    awaiting_numbers: bool = False
    current_index: int = 0
    correct_answers: int = 0
    selected_indexes: set[int] = field(default_factory=set)
    matching_step: int = 0
    matching_answers: list[list[int]] = field(default_factory=list)

    @property
    def total_questions(self) -> int:
        return len(self.questions)

    @property
    def current_question(self) -> Question:
        return self.questions[self.current_index]

    def mark_correct(self) -> None:
        self.correct_answers += 1

    def toggle_selected_index(self, option_index: int) -> None:
        if option_index in self.selected_indexes:
            self.selected_indexes.remove(option_index)
            return
        self.selected_indexes.add(option_index)

    def save_matching_step(self) -> None:
        self.matching_answers.append(sorted(self.selected_indexes))
        self.selected_indexes.clear()
        self.matching_step += 1

    def move_next(self) -> None:
        self.current_index += 1
        self.selected_indexes.clear()
        self.matching_step = 0
        self.matching_answers.clear()
