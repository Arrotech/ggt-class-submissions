"""Question validation and Markdown generation shared by the web and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from urllib.parse import urlparse


DIFFICULTIES = ("Easy", "Medium", "Hard")
MAX_QUESTIONS = 10
MAX_FIELD_LENGTH = 20_000


@dataclass(frozen=True)
class PracticeQuestion:
    title: str
    url: str
    difficulty: str
    approach: str
    solution: str
    reflection: str = ""


def validate_hackerrank_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and hostname in {"hackerrank.com", "www.hackerrank.com"}
        and parsed.username is None
        and parsed.password is None
        and bool(parsed.path)
    )


def slugify(title: str) -> str:
    """Create a lowercase filename-safe slug from a question title."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "question"


def question_markdown(topic: str, question: PracticeQuestion) -> str:
    """Render one completed question in the project's Markdown format."""
    longest_fence = max(
        (len(match.group()) for match in re.finditer(r"`+", question.solution)),
        default=0,
    )
    fence = "`" * max(3, longest_fence + 1)
    return f"""# {question.title}

> **Topic:** {topic}<br>
> **Difficulty:** {question.difficulty}<br>
> **HackerRank:** <{question.url}>

## Intuition / Approach

{question.approach}

## My Solution

{fence}sql
{question.solution}
{fence}

## Reflection

{question.reflection or "<!-- Note what you learned or what you would revisit. -->"}
"""


def date_folder(practice_date: date) -> str:
    return practice_date.strftime("%m-%d-%Y")
