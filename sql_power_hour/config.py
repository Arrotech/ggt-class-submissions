"""Application settings loaded from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    github_app_client_id: str
    github_app_client_secret: str
    github_app_slug: str
    session_secret: str
    app_base_url: str
    environment: str

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.environ.get("APP_ENV", "development").lower()
        session_secret = os.environ.get("SESSION_SECRET", "")
        if not session_secret:
            if environment == "production":
                raise RuntimeError("SESSION_SECRET must be configured in production.")
            session_secret = "local-development-only-change-before-deployment"
        elif environment == "production" and len(session_secret) < 32:
            raise RuntimeError("SESSION_SECRET must be at least 32 characters in production.")

        client_id = os.environ.get("GITHUB_APP_CLIENT_ID", "")
        client_secret = os.environ.get("GITHUB_APP_CLIENT_SECRET", "")
        app_slug = os.environ.get("GITHUB_APP_SLUG", "")
        if environment == "production" and not all((client_id, client_secret, app_slug)):
            raise RuntimeError(
                "GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET, and "
                "GITHUB_APP_SLUG must be configured in production."
            )

        base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
        if environment == "production" and not base_url.startswith("https://"):
            raise RuntimeError("APP_BASE_URL must use HTTPS in production.")

        return cls(
            github_app_client_id=client_id,
            github_app_client_secret=client_secret,
            github_app_slug=app_slug,
            session_secret=session_secret,
            app_base_url=base_url,
            environment=environment,
        )

    @property
    def secure_cookies(self) -> bool:
        return self.app_base_url.startswith("https://")

    @property
    def project_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent
