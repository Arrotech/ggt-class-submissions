"""GitHub API operations for repository selection and publishing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any
from urllib.parse import quote

import httpx

from sql_power_hour.content import PracticeQuestion, date_folder, question_markdown, slugify


class GitHubAPIError(RuntimeError):
    """A GitHub API request failed or returned an unexpected response."""


@dataclass(frozen=True)
class PublishedFile:
    path: str
    markdown: str


@dataclass(frozen=True)
class PublishResult:
    repository: str
    branch: str
    commit_sha: str
    files: tuple[PublishedFile, ...]


class GitHubClient:
    def __init__(self, access_token: str) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as error:
            raise GitHubAPIError(f"Could not connect to GitHub: {error}") from error
        if not response.is_success:
            try:
                response_body = response.json()
                detail = (
                    response_body.get("message", response.text)
                    if isinstance(response_body, dict)
                    else response.text
                )
            except ValueError:
                detail = response.text
            raise GitHubAPIError(f"GitHub API returned HTTP {response.status_code}: {detail}")
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise GitHubAPIError("GitHub returned an invalid JSON response.") from error

    def list_repositories(self) -> list[dict[str, Any]]:
        repositories = []
        page = 1
        while page <= 10:
            result = self.request(
                "GET",
                f"/user/repos?affiliation=owner,collaborator,organization_member"
                f"&sort=full_name&per_page=100&page={page}",
            )
            if not isinstance(result, list):
                raise GitHubAPIError("GitHub returned an unexpected repository list.")
            repositories.extend(
                {
                    "full_name": repository["full_name"],
                    "private": repository["private"],
                    "default_branch": repository["default_branch"],
                }
                for repository in result
                if repository.get("permissions", {}).get("push")
            )
            if len(result) < 100:
                break
            page += 1
        else:
            raise GitHubAPIError(
                "More than 1,000 writable repositories were found; narrow the GitHub App "
                "installation to the repositories you need."
            )
        return repositories

    def publish(
        self,
        repository: str,
        practice_date: date,
        topic: str,
        questions: list[PracticeQuestion],
    ) -> PublishResult:
        if (
            not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            or any(part in {".", ".."} for part in repository.split("/"))
        ):
            raise GitHubAPIError("Choose a valid repository in OWNER/REPO format.")

        repo_data = self.request("GET", f"/repos/{repository}")
        branch = repo_data.get("default_branch")
        if not branch:
            raise GitHubAPIError(
                "This repository has no default branch. Create an initial commit on GitHub first."
            )

        branch_ref = quote(branch, safe="/")
        ref = self.request("GET", f"/repos/{repository}/git/ref/heads/{branch_ref}")
        parent_sha = ref.get("object", {}).get("sha")
        if not parent_sha:
            raise GitHubAPIError(f"Could not determine the latest commit on {branch}.")

        parent = self.request("GET", f"/repos/{repository}/git/commits/{parent_sha}")
        base_tree_sha = parent.get("tree", {}).get("sha")
        if not base_tree_sha:
            raise GitHubAPIError("Could not determine the repository's latest Git tree.")

        tree_result = self.request(
            "GET", f"/repos/{repository}/git/trees/{base_tree_sha}?recursive=1"
        )
        if tree_result.get("truncated"):
            raise GitHubAPIError("The repository is too large to safely check for filename conflicts.")

        folder = date_folder(practice_date)
        used_numbers = set()
        for item in tree_result.get("tree", []):
            path = item.get("path", "")
            if path.startswith(f"{folder}/"):
                match = re.match(r"(\d+)-.+\.md$", path.rsplit("/", 1)[-1])
                if match:
                    used_numbers.add(int(match.group(1)))

        files = []
        tree_entries = []
        for question in questions:
            number = 1
            while number in used_numbers:
                number += 1
            used_numbers.add(number)
            path = f"{folder}/{number:03d}-{slugify(question.title)}.md"
            markdown = question_markdown(topic, question)
            files.append(PublishedFile(path=path, markdown=markdown))
            tree_entries.append(
                {
                    "path": path,
                    "mode": "100644",
                    "type": "blob",
                    "content": markdown,
                }
            )

        new_tree = self.request(
            "POST",
            f"/repos/{repository}/git/trees",
            {"base_tree": base_tree_sha, "tree": tree_entries},
        )
        tree_sha = new_tree.get("sha")
        if not tree_sha:
            raise GitHubAPIError("GitHub did not return the new tree ID.")

        commit = self.request(
            "POST",
            f"/repos/{repository}/git/commits",
            {
                "message": f"Add SQL practice questions for {folder}",
                "tree": tree_sha,
                "parents": [parent_sha],
            },
        )
        commit_sha = commit.get("sha")
        if not commit_sha:
            raise GitHubAPIError("GitHub did not return the new commit ID.")

        self.request(
            "PATCH",
            f"/repos/{repository}/git/refs/heads/{branch_ref}",
            {"sha": commit_sha, "force": False},
        )
        return PublishResult(repository, branch, commit_sha, tuple(files))
