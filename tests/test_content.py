from datetime import date
import unittest

from sql_power_hour.content import (
    PracticeQuestion,
    date_folder,
    question_markdown,
    slugify,
    validate_hackerrank_url,
)


class QuestionContentTests(unittest.TestCase):
    def test_date_folder_uses_month_day_year(self) -> None:
        self.assertEqual(date_folder(date(2026, 10, 13)), "10-13-2026")

    def test_slug_is_safe_for_question_filename(self) -> None:
        self.assertEqual(slugify("Weather Observation Station #1"), "weather-observation-station-1")
        self.assertEqual(slugify("???"), "question")

    def test_only_https_hackerrank_challenge_urls_are_accepted(self) -> None:
        self.assertTrue(
            validate_hackerrank_url(
                "https://www.hackerrank.com/challenges/select-all"
            )
        )
        self.assertFalse(validate_hackerrank_url("http://www.hackerrank.com/challenges/select-all"))
        self.assertFalse(validate_hackerrank_url("https://example.com/challenge"))
        self.assertFalse(validate_hackerrank_url("https://["))

    def test_markdown_contains_required_sections_and_sql_fence(self) -> None:
        question = PracticeQuestion(
            title="Select All",
            url="https://www.hackerrank.com/challenges/select-all",
            difficulty="Easy",
            approach="Select every column from the table.",
            solution="SELECT * FROM CITY;",
            reflection="I learned how the table is structured.",
        )

        markdown = question_markdown("SELECT", question)

        self.assertIn("> **Topic:** SELECT", markdown)
        self.assertIn("> **Difficulty:** Easy", markdown)
        self.assertIn("> **HackerRank:** <https://www.hackerrank.com/challenges/select-all>", markdown)
        self.assertIn("## Intuition / Approach", markdown)
        self.assertIn("```sql\nSELECT * FROM CITY;\n```", markdown)
        self.assertIn(
            "## Reflection\n\nI learned how the table is structured.",
            markdown,
        )

    def test_sql_fence_is_longer_than_fences_inside_solution(self) -> None:
        question = PracticeQuestion(
            title="Fenced Example",
            url="https://www.hackerrank.com/challenges/select-all",
            difficulty="Medium",
            approach="Keep embedded examples intact.",
            solution="-- ```sql\nSELECT 1;",
        )

        markdown = question_markdown("Comments", question)

        self.assertIn("````sql\n-- ```sql\nSELECT 1;\n````", markdown)


if __name__ == "__main__":
    unittest.main()
