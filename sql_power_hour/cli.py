"""Local-only fallback for creating blank SQL question templates."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from sql_power_hour.content import date_folder, slugify


PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_QUESTION_COUNT = 3


def ask_for_date() -> date:
    while True:
        value = input(f"Practice date [{date.today().strftime('%m-%d-%Y')}]: ").strip()
        if not value:
            return date.today()
        try:
            parsed = datetime.strptime(value, "%m-%d-%Y").date()
            if parsed.strftime("%m-%d-%Y") != value:
                raise ValueError
            return parsed
        except ValueError:
            print("Enter a valid date in MM-DD-YYYY format.")


def ask_for_count() -> int:
    while True:
        value = input(f"Number of questions [{DEFAULT_QUESTION_COUNT}]: ").strip()
        if not value:
            return DEFAULT_QUESTION_COUNT
        try:
            count = int(value)
            if count > 0:
                return count
        except ValueError:
            pass
        print("Enter a whole number greater than zero.")


def question_template(title: str) -> str:
    return f"""# {title}

> **Topic:** Add the SQL topic<br>
> **Difficulty:** Choose Easy, Medium, or Hard<br>
> **HackerRank:** [Add the question link](PASTE_HACKERRANK_URL_HERE)

## Intuition / Approach

<!-- Describe how you plan to solve the problem before writing SQL. -->

## My Solution

```sql
-- Write your SQL solution here.
```

## Reflection

<!-- Note what you learned or what you would revisit. -->
"""


def create_question(folder: Path, title: str, number: int) -> Path:
    while True:
        if any(folder.glob(f"{number:03d}-*.md")):
            number += 1
            continue
        path = folder / f"{number:03d}-{slugify(title)}.md"
        try:
            with path.open("x", encoding="utf-8", newline="\n") as question_file:
                question_file.write(question_template(title))
            return path
        except FileExistsError:
            number += 1


def main() -> int:
    print("SQL Power Hour - local question templates")
    practice_date = ask_for_date()
    count = ask_for_count()
    folder = PROJECT_DIR / date_folder(practice_date)
    folder.mkdir(parents=True, exist_ok=True)
    for number in range(1, count + 1):
        title = input(f"Question {number} title: ").strip() or f"HackerRank Question {number}"
        created = create_question(folder, title, number)
        print(f"Created {created.relative_to(PROJECT_DIR)}")
    return 0
