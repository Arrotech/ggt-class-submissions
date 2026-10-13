"""Practice-session entry and publication routes."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, Response

from sql_power_hour.auth import UserToken, new_state, set_token_cookie
from sql_power_hour.config import Settings
from sql_power_hour.content import DIFFICULTIES, date_folder
from sql_power_hour.forms import (
    empty_question,
    parse_questions,
    question_form_values,
    validate_session,
)
from sql_power_hour.github_api import GitHubAPIError
from sql_power_hour.web_helpers import (
    get_token,
    github_client,
    render_page,
    valid_csrf,
    writable_repositories,
)


router = APIRouter()


@router.get("/")
def home(request: Request) -> Response:
    token = get_token(request)
    username = request.session.get("github_login")
    if token is None or not username:
        return render_page(
            request,
            "login.html",
            error=request.session.pop("auth_error", None),
        )

    repositories, error = writable_repositories(token)
    response = render_page(
        request,
        "dashboard.html",
        username=username,
        repositories=repositories,
        error=error,
        practice_date=date.today().isoformat(),
        topic="",
        questions=[empty_question()],
        difficulties=DIFFICULTIES,
    )
    update_token_cookie(response, token, request)
    return response


@router.post("/publish")
async def publish(request: Request) -> Response:
    form = await request.form()
    if not valid_csrf(request, str(form.get("csrf_token", ""))):
        return render_page(request, "login.html", error="The form expired. Please sign in again.")

    token = get_token(request)
    username = request.session.get("github_login")
    if token is None or not username:
        return RedirectResponse("/", status_code=303)

    topic, practice_date, errors = validate_session(
        str(form.get("topic", "")),
        str(form.get("practice_date", "")),
    )
    repository = str(form.get("repository", "")).strip()
    questions, question_errors = parse_questions(form)
    errors.extend(question_errors)
    if not repository:
        errors.append("Choose a GitHub repository.")

    if errors or practice_date is None:
        repositories, repo_error = writable_repositories(token)
        if repo_error:
            errors.append(repo_error)
        response = render_page(
            request,
            "dashboard.html",
            username=username,
            repositories=repositories,
            error=" ".join(errors),
            practice_date=str(form.get("practice_date", "")),
            topic=topic,
            questions=question_form_values(form),
            difficulties=DIFFICULTIES,
            selected_repository=repository,
        )
        update_token_cookie(response, token, request)
        return response

    client = github_client(token)
    try:
        result = client.publish(repository, practice_date, topic, questions)
    except GitHubAPIError as exception:
        repositories, repo_error = writable_repositories(token)
        display_error = str(exception)
        if repo_error:
            display_error = f"{display_error} Repository list could not be refreshed: {repo_error}"
        response = render_page(
            request,
            "dashboard.html",
            username=username,
            repositories=repositories,
            error=display_error,
            practice_date=str(form.get("practice_date", "")),
            topic=topic,
            questions=question_form_values(form),
            difficulties=DIFFICULTIES,
            selected_repository=repository,
        )
        update_token_cookie(response, token, request)
        return response
    finally:
        client.close()

    request.session["last_publish"] = {
        "repository": result.repository,
        "branch": result.branch,
        "commit_sha": result.commit_sha,
        "date": date_folder(practice_date),
        "paths": [file.path for file in result.files],
    }
    request.session["csrf_token"] = new_state()
    response = render_page(
        request,
        "published.html",
        username=username,
        result=result,
        file_links=[
            (
                file.path,
                f"https://github.com/{result.repository}/blob/"
                f"{quote(result.commit_sha, safe='')}/{quote(file.path, safe='/')}",
            )
            for file in result.files
        ],
    )
    update_token_cookie(response, token, request)
    return response


def update_token_cookie(response: Response, token: UserToken, request: Request) -> None:
    settings: Settings = request.app.state.settings
    set_token_cookie(response, token, settings)
