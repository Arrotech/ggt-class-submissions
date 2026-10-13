"""GitHub App OAuth helpers and encrypted browser token storage."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import urlencode

from cryptography.fernet import Fernet, InvalidToken
import httpx
from starlette.requests import Request
from starlette.responses import Response

from sql_power_hour.config import Settings


TOKEN_COOKIE = "sql_power_hour_token"
TOKEN_COOKIE_MAX_AGE = 60 * 60 * 24 * 30


@dataclass(frozen=True)
class UserToken:
    access_token: str
    refresh_token: str | None
    expires_at: float | None
    refresh_expires_at: float | None

    def serialize(self) -> bytes:
        return json.dumps(self.__dict__).encode("utf-8")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "UserToken":
        return cls(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token"),
            expires_at=payload.get("expires_at"),
            refresh_expires_at=payload.get("refresh_expires_at"),
        )


class TokenVault:
    def __init__(self, session_secret: str) -> None:
        key_material = hashlib.sha256(session_secret.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(key_material))

    def seal(self, token: UserToken) -> str:
        return self._fernet.encrypt(token.serialize()).decode("ascii")

    def open(self, ciphertext: str) -> UserToken:
        try:
            payload = json.loads(self._fernet.decrypt(ciphertext.encode("ascii")))
            if not isinstance(payload, dict):
                raise ValueError("Your GitHub session is invalid. Please sign in again.")
            return UserToken.from_payload(payload)
        except (
            InvalidToken,
            UnicodeDecodeError,
            UnicodeEncodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
        ) as error:
            raise ValueError("Your GitHub session is invalid. Please sign in again.") from error


def oauth_authorization_url(settings: Settings, state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.github_app_client_id,
            "redirect_uri": f"{settings.app_base_url}/auth/callback",
            "state": state,
            "allow_signup": "true",
        }
    )
    return f"https://github.com/login/oauth/authorize?{query}"


def exchange_code(settings: Settings, code: str) -> UserToken:
    try:
        response = httpx.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_app_client_id,
                "client_secret": settings.github_app_client_secret,
                "code": code,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError("GitHub sign-in failed. Please try again.") from error
    if not isinstance(result, dict):
        raise RuntimeError("GitHub returned an unexpected sign-in response.")
    if result.get("error") or not result.get("access_token"):
        raise RuntimeError(result.get("error_description", "GitHub did not authorize the app."))

    now = time.time()
    expires_in = result.get("expires_in")
    refresh_expires_in = result.get("refresh_token_expires_in")
    return UserToken(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token"),
        expires_at=now + expires_in if expires_in else None,
        refresh_expires_at=now + refresh_expires_in if refresh_expires_in else None,
    )


def current_token(request: Request, settings: Settings) -> UserToken | None:
    encrypted = request.cookies.get(TOKEN_COOKIE)
    if not encrypted:
        return None
    return TokenVault(settings.session_secret).open(encrypted)


def refreshed_token(token: UserToken, settings: Settings) -> UserToken:
    if token.expires_at is None or token.expires_at > time.time() + 60:
        return token
    if not token.refresh_token or (
        token.refresh_expires_at is not None and token.refresh_expires_at <= time.time()
    ):
        raise ValueError("Your GitHub sign-in expired. Please sign in again.")

    try:
        response = httpx.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_app_client_id,
                "client_secret": settings.github_app_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
            timeout=15.0,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise RuntimeError("Could not refresh your GitHub sign-in. Please try again.") from error

    if not isinstance(result, dict):
        raise RuntimeError("GitHub returned an unexpected refresh response.")
    if result.get("error") or not result.get("access_token"):
        raise ValueError("Your GitHub sign-in expired. Please sign in again.")
    now = time.time()
    return UserToken(
        access_token=result["access_token"],
        refresh_token=result.get("refresh_token", token.refresh_token),
        expires_at=now + result["expires_in"] if result.get("expires_in") else None,
        refresh_expires_at=(
            now + result["refresh_token_expires_in"]
            if result.get("refresh_token_expires_in")
            else token.refresh_expires_at
        ),
    )


def set_token_cookie(response: Response, token: UserToken, settings: Settings) -> None:
    response.set_cookie(
        TOKEN_COOKIE,
        TokenVault(settings.session_secret).seal(token),
        max_age=TOKEN_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def new_state() -> str:
    return secrets.token_urlsafe(32)
