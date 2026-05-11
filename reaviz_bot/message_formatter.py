from __future__ import annotations

from reaviz_bot.constants import OPTION_LETTERS
from reaviz_bot.models import Question, TestSession


class QuestionMessageFormatter:
    def format_question(self, session: TestSession) -> str:
        question = session.current_question
        options_text = self.format_options(question)
        header = (
            f"Вопрос {session.current_index + 1} из {session.total_questions}"
            f"\n\n{question.text}\n\n{options_text}"
        )
        return header + self._prompt_for(question, session)

    def format_options(self, question: Question) -> str:
        lines = []
        for index, option in enumerate(question.options):
            letter = OPTION_LETTERS[index]
            lines.append(f"{letter}) {option}")
        return "\n".join(lines)

    def _prompt_for(self, question: Question, session: TestSession) -> str:
        if question.is_matching:
            labels_text = ", ".join(question.matching_labels)
            return (
                "\n\nЭто задание на соответствие."
                f"\nВыбирайте ответы по порядку для пунктов: {labels_text}."
                f"\nСейчас выберите вариант(ы) для пункта {question.matching_labels[session.matching_step]}."
                "\n\nНажимайте кнопки с номерами вариантов ниже."
            )

        if question.has_multiple_answers:
            return (
                "\n\nВ этом вопросе может быть несколько правильных ответов."
                "\nВыберите все подходящие буквы и нажмите «Ответить»."
            )

        return "\n\nВыберите букву правильного варианта."

