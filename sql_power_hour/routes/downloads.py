"""Download route for recently published question files."""

from __future__ import annotations

import base64
import io
import re
import zipfile

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, Response, StreamingResponse

from sql_power_hour.auth import set_token_cookie
from sql_power_hour.content import DIFFICULTIES
from sql_power_hour.forms import empty_question
from sql_power_hour.github_api import GitHubAPIError
from sql_power_hour.web_helpers import (
    get_token,
    github_client,
    render_page,
    writable_repositories,
)


router = APIRouter()


@router.get("/download")
def download(request: Request) -> Response:
    token = get_token(request)
    username = request.session.get("github_login")
    publication = request.session.get("last_publish")
    if token is None or not username:
        return RedirectResponse("/", status_code=303)
    if not publication:
        response = render_page(
            request,
            "dashboard.html",
            username=username,
            repositories=[],
            error="There is no published session to download yet.",
            practice_date="",
            topic="",
            questions=[empty_question()],
            difficulties=DIFFICULTIES,
        )
        set_token_cookie(response, token, request.app.state.settings)
        return response

    archive = io.BytesIO()
    client = github_client(token)
    try:
        with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for path in publication["paths"]:
                if not re.fullmatch(r"\d{2}-\d{2}-\d{4}/\d{3,}-[a-z0-9-]+\.md", path):
                    raise GitHubAPIError("The saved download file path is invalid.")
                file_data = client.request(
                    "GET",
                    f"/repos/{publication['repository']}/contents/{path}"
                    f"?ref={publication['commit_sha']}",
                )
                if file_data.get("encoding") != "base64":
                    raise GitHubAPIError(f"GitHub could not provide {path} as a file.")
                bundle.writestr(path, base64.b64decode(file_data["content"]))
    except (GitHubAPIError, ValueError, KeyError) as exception:
        repositories, repo_error = writable_repositories(token)
        display_error = f"Could not prepare the download: {exception}"
        if repo_error:
            display_error = f"{display_error} Repository list could not be refreshed: {repo_error}"
        response = render_page(
            request,
            "dashboard.html",
            username=username,
            repositories=repositories,
            error=display_error,
            practice_date="",
            topic="",
            questions=[empty_question()],
            difficulties=DIFFICULTIES,
        )
        set_token_cookie(response, token, request.app.state.settings)
        return response
    finally:
        client.close()

    archive.seek(0)
    filename = f"sql-practice-{publication['date']}.zip"
    response = StreamingResponse(
        archive,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
    set_token_cookie(response, token, request.app.state.settings)
    return response
