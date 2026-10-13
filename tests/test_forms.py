from datetime import date
import unittest

from starlette.datastructures import FormData

from sql_power_hour.forms import parse_questions, validate_session


class FormValidationTests(unittest.TestCase):
    def test_valid_question_is_parsed(self) -> None:
        form = FormData(
            [
                ("question_title", "Select All"),
                ("question_url", "https://www.hackerrank.com/challenges/select-all"),
                ("difficulty", "Easy"),
                ("approach", "Return all columns from the table."),
                ("solution", "SELECT * FROM CITY;"),
            ]
        )

        questions, errors = parse_questions(form)

        self.assertEqual(errors, [])
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].title, "Select All")
        self.assertEqual(questions[0].difficulty, "Easy")

    def test_question_with_non_hackerrank_link_is_rejected(self) -> None:
        form = FormData(
            [
                ("question_title", "Select All"),
                ("question_url", "https://example.com/challenge"),
                ("difficulty", "Easy"),
                ("approach", "Return all columns."),
                ("solution", "SELECT * FROM CITY;"),
            ]
        )

        _, errors = parse_questions(form)

        self.assertTrue(any("HackerRank URL" in error for error in errors))

    def test_non_text_question_fields_are_rejected_without_crashing(self) -> None:
        form = FormData(
            [
                ("question_title", object()),
                ("question_url", "https://www.hackerrank.com/challenges/select-all"),
            ]
        )

        _, errors = parse_questions(form)

        self.assertIn("Question fields must contain text.", errors)

    def test_session_date_is_parsed(self) -> None:
        topic, practice_date, errors = validate_session("Aggregates", "2026-10-13")

        self.assertEqual(topic, "Aggregates")
        self.assertEqual(practice_date, date(2026, 10, 13))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
