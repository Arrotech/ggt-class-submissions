"""Parsing and validation for submitted practice-session forms."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sql_power_hour.content import (
    DIFFICULTIES,
    MAX_FIELD_LENGTH,
    MAX_QUESTIONS,
    PracticeQuestion,
    validate_hackerrank_url,
)


MAX_TITLE_LENGTH = 100
MAX_TOPIC_LENGTH = 120


def empty_question() -> dict[str, str]:
    return {
        "title": "",
        "url": "",
        "difficulty": "",
        "approach": "",
        "solution": "",
        "reflection": "",
    }


def question_form_values(form: Any) -> list[dict[str, str]]:
    keys = (
        "question_title",
        "question_url",
        "difficulty",
        "approach",
        "solution",
        "reflection",
    )
    values = {
        key: [value if isinstance(value, str) else "" for value in form.getlist(key)]
        for key in keys
    }
    row_count = max(1, max((len(items) for items in values.values()), default=0))
    return [
        {
            "title": (
                values["question_title"][index]
                if index < len(values["question_title"])
                else ""
            ),
            "url": (
                values["question_url"][index]
                if index < len(values["question_url"])
                else ""
            ),
            "difficulty": (
                values["difficulty"][index]
                if index < len(values["difficulty"])
                else ""
            ),
            "approach": values["approach"][index] if index < len(values["approach"]) else "",
            "solution": values["solution"][index] if index < len(values["solution"]) else "",
            "reflection": (
                values["reflection"][index]
                if index < len(values["reflection"])
                else ""
            ),
        }
        for index in range(row_count)
    ]


def parse_questions(form: Any) -> tuple[list[PracticeQuestion], list[str]]:
    questions = []
    keys = (
        "question_title",
        "question_url",
        "difficulty",
        "approach",
        "solution",
        "reflection",
    )
    has_non_text_value = any(
        not isinstance(value, str)
        for key in keys
        for value in form.getlist(key)
    )
    errors = ["Question fields must contain text."] if has_non_text_value else []
    for index, values in enumerate(question_form_values(form), start=1):
        title = values["title"].strip()
        url = values["url"].strip()
        difficulty = values["difficulty"].strip()
        approach = values["approach"].strip()
        solution = values["solution"].strip()
        reflection = values["reflection"].strip()
        if not any((title, url, difficulty, approach, solution, reflection)):
            errors.append(f"Question {index} is empty.")
            continue
        if not title or len(title) > MAX_TITLE_LENGTH or "\n" in title:
            errors.append(
                f"Question {index}: title must be on one line and at most "
                f"{MAX_TITLE_LENGTH} characters."
            )
        if not validate_hackerrank_url(url):
            errors.append(f"Question {index}: enter a valid HTTPS HackerRank URL.")
        if difficulty not in DIFFICULTIES:
            errors.append(f"Question {index}: select Easy, Medium, or Hard.")
        if not approach or not solution:
            errors.append(f"Question {index}: approach and SQL solution are required.")
        if any(
            len(value) > MAX_FIELD_LENGTH
            for value in (approach, solution, reflection)
        ):
            errors.append(
                f"Question {index}: approach, SQL solution, and reflection must each be under "
                f"{MAX_FIELD_LENGTH:,} characters."
            )
        questions.append(
            PracticeQuestion(title, url, difficulty, approach, solution, reflection)
        )

    if len(questions) > MAX_QUESTIONS:
        errors.append(f"You can publish up to {MAX_QUESTIONS} questions at a time.")
    return questions, errors


def validate_session(
    topic_value: str, date_value: str
) -> tuple[str, date | None, list[str]]:
    topic = topic_value.strip()
    errors = []
    if not topic or len(topic) > MAX_TOPIC_LENGTH or "\n" in topic:
        errors.append(
            f"Enter a topic on one line (up to {MAX_TOPIC_LENGTH} characters)."
        )
    try:
        practice_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    except ValueError:
        practice_date = None
        errors.append("Choose a valid practice date.")
    return topic, practice_date, errors
