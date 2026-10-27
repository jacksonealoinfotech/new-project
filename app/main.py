"""FastAPI application factory and entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.error_handlers import register_error_handlers
from app.core.lifecycle import lifespan
from app.core.middleware import register_middlewares


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct and configure FastAPI application instance."""
    app_settings = settings or get_settings()

    # Disable interactive documentation in production unless explicitly enabled
    docs_url = "/docs" if not app_settings.APP_ENV.is_production else None
    redoc_url = "/redoc" if not app_settings.APP_ENV.is_production else None
    openapi_url = "/openapi.json" if not app_settings.APP_ENV.is_production else None

    app = FastAPI(
        title=app_settings.APP_NAME,
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # --- CORS Middleware ---
    if app_settings.ALLOWED_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=app_settings.ALLOWED_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # --- Trusted Host Middleware (Production & Staging) ---
    if app_settings.APP_ENV.is_production and app_settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=app_settings.ALLOWED_HOSTS,
        )

    # --- Custom Middlewares (Request ID, Logging, Security Headers) ---
    register_middlewares(app)

    # --- Centralized Exception Handlers ---
    register_error_handlers(app)

    # --- Include API Routers ---
    app.include_router(api_router)

    return app


app = create_app()
