from __future__ import annotations

import re

from reaviz_bot.constants import LATIN_TO_CYRILLIC, LETTER_TO_INDEX, OPTION_LETTERS


class AnswerParser:
    def normalize_answer_string(self, raw_value: str) -> str:
        normalized = str(raw_value).lower().replace(" ", "")
        for latin, cyrillic in LATIN_TO_CYRILLIC.items():
            normalized = normalized.replace(latin, cyrillic)
        return normalized

    def parse_correct_indexes(self, raw_value: str) -> list[int]:
        indexes = []
        seen = set()
        digits = re.findall(r"\d", str(raw_value))
        if digits:
            for digit in digits:
                index = int(digit) - 1
                if 0 <= index < len(OPTION_LETTERS) and index not in seen:
                    indexes.append(index)
                    seen.add(index)
            if indexes:
                return indexes

        found_letters = re.findall(r"[а-яa-z]", str(raw_value).lower())
        for letter in found_letters:
            letter = LATIN_TO_CYRILLIC.get(letter, letter)
            index = LETTER_TO_INDEX.get(letter)
            if index is not None and index not in seen:
                indexes.append(index)
                seen.add(index)
        return indexes

    def parse_matching_groups(self, raw_value: str, options_count: int) -> tuple[list[str], list[list[int]]]:
        normalized = self.normalize_answer_string(raw_value)
        groups_with_letters = re.findall(r"([абвгдежзи])(\d+)", normalized)
        if groups_with_letters:
            labels = []
            groups = []
            for label, digits in groups_with_letters:
                labels.append(label)
                groups.append([int(digit) - 1 for digit in digits if digit.isdigit()])
            return labels, groups

        digits = [int(digit) - 1 for digit in normalized if digit.isdigit()]
        labels = OPTION_LETTERS[: min(len(digits), options_count)]
        groups = [[digit] for digit in digits]
        return labels, groups

    def detect_question_type(self, raw_value: str) -> str:
        normalized = self.normalize_answer_string(raw_value)
        if any(char.isdigit() for char in normalized):
            return "matching"

        correct_indexes = self.parse_correct_indexes(raw_value)
        if len(correct_indexes) > 1:
            return "multi"
        return "single"

