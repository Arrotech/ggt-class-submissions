"""Sign-in and sign-out routes."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse, Response

from sql_power_hour.auth import (
    TOKEN_COOKIE,
    exchange_code,
    new_state,
    oauth_authorization_url,
    set_token_cookie,
)
from sql_power_hour.config import Settings
from sql_power_hour.github_api import GitHubAPIError
from sql_power_hour.web_helpers import github_client, render_page, valid_csrf


router = APIRouter()


@router.get("/login")
def login(request: Request) -> Response:
    settings: Settings = request.app.state.settings
    if not all(
        (
            settings.github_app_client_id,
            settings.github_app_client_secret,
            settings.github_app_slug,
        )
    ):
        return render_page(request, "login.html")
    state = new_state()
    request.session["oauth_state"] = state
    return RedirectResponse(oauth_authorization_url(settings, state), status_code=303)


@router.get("/auth/callback")
def oauth_callback(
    request: Request, code: str = "", state: str = "", error: str = ""
) -> Response:
    settings: Settings = request.app.state.settings
    expected_state = request.session.pop("oauth_state", "")
    if error:
        return render_page(request, "login.html", error="GitHub sign-in was cancelled.")
    if not code or not expected_state or not hmac.compare_digest(expected_state, state):
        return render_page(
            request,
            "login.html",
            error="GitHub sign-in could not be verified. Try again.",
        )

    try:
        token = exchange_code(settings, code)
        client = github_client(token)
        try:
            profile = client.request("GET", "/user")
        finally:
            client.close()
    except (RuntimeError, GitHubAPIError) as exception:
        return render_page(request, "login.html", error=str(exception))

    if not isinstance(profile, dict):
        return render_page(
            request,
            "login.html",
            error="GitHub returned an unexpected account profile. Please sign in again.",
        )
    login_name = profile.get("login")
    if not login_name:
        return render_page(
            request,
            "login.html",
            error="GitHub did not return your account name. Please sign in again.",
        )
    request.session.clear()
    request.session["github_login"] = login_name
    request.session["csrf_token"] = new_state()
    response = RedirectResponse("/", status_code=303)
    set_token_cookie(response, token, settings)
    return response


@router.post("/logout")
async def logout(request: Request) -> Response:
    form = await request.form()
    if not valid_csrf(request, str(form.get("csrf_token", ""))):
        return render_page(request, "login.html", error="The form expired. Please try again.")
    request.session.clear()
    settings: Settings = request.app.state.settings
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(
        TOKEN_COOKIE,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    return response
