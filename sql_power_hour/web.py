"""FastAPI application setup shared by local development and Vercel."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from sql_power_hour.config import Settings
from sql_power_hour.routes.auth import router as auth_router
from sql_power_hour.routes.downloads import router as download_router
from sql_power_hour.routes.practice import router as practice_router


def create_app() -> FastAPI:
    settings = Settings.from_environment()
    app = FastAPI(title="SQL Power Hour", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="sql_power_hour_session",
        max_age=60 * 60 * 8,
        same_site="lax",
        https_only=settings.secure_cookies,
    )

    @app.middleware("http")
    async def add_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; form-action 'self' https://github.com; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
        return response

    app.mount(
        "/static",
        StaticFiles(directory=str(settings.project_dir / "static")),
        name="static",
    )
    app.include_router(auth_router)
    app.include_router(practice_router)
    app.include_router(download_router)
    return app
