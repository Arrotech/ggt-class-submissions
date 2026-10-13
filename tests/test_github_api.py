import unittest
from datetime import date

from sql_power_hour.github_api import GitHubAPIError, GitHubClient


class GitHubClientTests(unittest.TestCase):
    def test_api_requests_use_the_signed_in_users_bearer_token(self) -> None:
        client = GitHubClient("test-access-token")
        try:
            self.assertEqual(
                client._client.headers["Authorization"],
                "Bearer test-access-token",
            )
        finally:
            client.close()

    def test_repository_path_segments_cannot_be_dot_segments(self) -> None:
        client = GitHubClient("test-access-token")
        try:
            for repository in ("../repo", "owner/..", "./repo", "owner/."):
                with self.subTest(repository=repository):
                    with self.assertRaisesRegex(GitHubAPIError, "valid repository"):
                        client.publish(repository, date(2026, 10, 13), "Topic", [])
        finally:
            client.close()


if __name__ == "__main__":
    unittest.main()
