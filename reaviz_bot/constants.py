from __future__ import annotations


START_BUTTON = "Начать тест"
CHOOSE_COUNT_BUTTON = "Выбрать количество вопросов"
CHOOSE_NUMBERS_BUTTON = "Выбрать номера вопросов"
STOP_TEST_BUTTON = "Остановить тест"
CHANGE_SUBJECT_BUTTON = "Сменить предмет"

ANATOMY_SUBJECT = "anatomy"
HISTOLOGY_SUBJECT = "histology"

# Порядок ключей задаёт порядок кнопок в меню выбора предмета.
SUBJECT_NAMES = {
    ANATOMY_SUBJECT: "Анатомия",
    HISTOLOGY_SUBJECT: "Гистология",
}
# Форма в родительном падеже для фраз вида «тесты по анатомии».
SUBJECT_NAMES_GENITIVE = {
    ANATOMY_SUBJECT: "анатомии",
    HISTOLOGY_SUBJECT: "гистологии",
}
SUBJECT_BUTTONS = {name: subject for subject, name in SUBJECT_NAMES.items()}

OPTION_LETTERS = ["а", "б", "в", "г", "д", "е", "ж", "з", "и"]
LETTER_TO_INDEX = {letter: index for index, letter in enumerate(OPTION_LETTERS)}
LATIN_TO_CYRILLIC = {
    "a": "а",
    "b": "б",
    "c": "в",
    "d": "г",
    "e": "д",
    "f": "е",
    "g": "ж",
    "h": "з",
    "i": "и",
}
