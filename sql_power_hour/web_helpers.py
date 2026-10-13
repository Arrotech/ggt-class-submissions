"""Shared helpers used by web route modules."""

from __future__ import annotations

import hmac
import secrets
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from sql_power_hour.auth import (
    UserToken,
    current_token,
    refreshed_token,
)
from sql_power_hour.config import Settings
from sql_power_hour.github_api import GitHubAPIError, GitHubClient


PROJECT_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(PROJECT_DIR / "templates"))


def render_page(request: Request, name: str, **context: object) -> HTMLResponse:
    settings: Settings = request.app.state.settings
    csrf_token = request.session.get("csrf_token")
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = csrf_token
    return templates.TemplateResponse(
        request=request,
        name=name,
        context={
            "request": request,
            "csrf_token": csrf_token,
            "github_configured": bool(
                settings.github_app_client_id
                and settings.github_app_client_secret
                and settings.github_app_slug
            ),
            "github_app_slug": settings.github_app_slug,
            **context,
        },
    )


def get_token(request: Request) -> UserToken | None:
    settings: Settings = request.app.state.settings
    try:
        token = current_token(request, settings)
        if token is None:
            return None
        return refreshed_token(token, settings)
    except (RuntimeError, ValueError) as error:
        request.session["auth_error"] = str(error)
        return None


def valid_csrf(request: Request, submitted: str) -> bool:
    expected = request.session.get("csrf_token", "")
    return bool(expected) and hmac.compare_digest(expected, submitted)


def github_client(token: UserToken) -> GitHubClient:
    return GitHubClient(token.access_token)


def writable_repositories(token: UserToken) -> tuple[list[dict[str, object]], str | None]:
    client = github_client(token)
    try:
        return client.list_repositories(), None
    except GitHubAPIError as error:
        return [], str(error)
    finally:
        client.close()
