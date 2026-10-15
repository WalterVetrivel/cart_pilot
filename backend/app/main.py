"""CartPilot API entry point (FastAPI, served on Cloud Run)."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import register_error_handlers
from app.routers import health, optimise, orders, parse, vouchers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="CartPilot API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    # Later milestones add: chat, live.
    app.include_router(health.router, prefix="/api")
    app.include_router(parse.router, prefix="/api")
    app.include_router(optimise.router, prefix="/api")
    app.include_router(vouchers.router, prefix="/api")
    app.include_router(orders.router, prefix="/api")
    return app


app = create_app()
