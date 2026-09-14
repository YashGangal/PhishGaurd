"""FastAPI application factory and cross-cutting middleware."""

from contextlib import asynccontextmanager
import logging

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.models.database import init_db
from app.routers import history, model_info, predict

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the PhishGuard API application."""

    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        """Initialize the database and load the model before serving requests."""

        init_db()
        from app.services.prediction import load_bundle
        load_bundle()
        logger.info("application_started")
        yield

    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Explainable phishing URL detection API",
        lifespan=lifespan,
        # Default docs disabled so /docs below can inject the bench theme.
        docs_url=None,
    )
    application.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")

    @application.get("/docs", include_in_schema=False)
    async def themed_docs() -> HTMLResponse:
        """Serve Swagger UI with the forensic bench stylesheet layered on top."""

        base = get_swagger_ui_html(
            openapi_url=application.openapi_url,
            title=f"{settings.app_name} — API console",
        )
        html = base.body.decode("utf-8").replace(
            "</head>",
            '<link type="text/css" rel="stylesheet" href="/static/swagger-dark.css"></head>',
        )
        return HTMLResponse(html)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Return the standard 422 error shape for invalid inputs."""

        logger.warning("request_validation_failed", extra={"path": str(request.url.path)})
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Prevent internal details from leaking while logging the exception."""

        logger.exception("unhandled_request_error", extra={"path": str(request.url.path)}, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    application.include_router(predict.router)
    application.include_router(history.router)
    application.include_router(model_info.router)
    return application


app = create_app()
