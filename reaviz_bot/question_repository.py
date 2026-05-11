from __future__ import annotations

import re
from pathlib import Path

import openpyxl

from reaviz_bot.models import Question
from reaviz_bot.question_parser import AnswerParser
from reaviz_bot.text_utils import normalize_spaces, strip_option_prefix


class ExcelQuestionRepository:
    def __init__(self, xlsx_path: Path, answer_parser: AnswerParser | None = None) -> None:
        self.xlsx_path = xlsx_path
        self.answer_parser = answer_parser or AnswerParser()

    def load_questions(self) -> list[Question]:
        workbook = openpyxl.load_workbook(self.xlsx_path, read_only=True, data_only=True)
        sheet = workbook[workbook.sheetnames[0]]
        questions: list[Question] = []

        for row in sheet.iter_rows(min_row=2, values_only=True):
            question = self._parse_row(row, len(questions) + 1)
            if question is not None:
                questions.append(question)

        return questions

    def _parse_row(self, row: tuple[object, ...], fallback_id: int) -> Question | None:
        if not row or not row[0]:
            return None

        question_text = normalize_spaces(str(row[0]))
        options = [strip_option_prefix(str(value)) for value in row[1:-1] if value]
        raw_answer = str(row[-1])
        question_type = self.answer_parser.detect_question_type(raw_answer)
        correct_indexes = self.answer_parser.parse_correct_indexes(raw_answer)
        matching_labels: list[str] = []
        matching_groups: list[list[int]] = []

        if question_type == "matching":
            matching_labels, matching_groups = self.answer_parser.parse_matching_groups(raw_answer, len(options))

        question_number_match = re.match(r"^\s*(\d+)", question_text)
        question_id = int(question_number_match.group(1)) if question_number_match else fallback_id

        if not question_text or not options or not (correct_indexes or matching_groups):
            return None

        return Question(
            question_id=question_id,
            text=question_text,
            options=options,
            correct_indexes=correct_indexes,
            question_type=question_type,
            matching_labels=matching_labels,
            matching_groups=matching_groups,
        )

