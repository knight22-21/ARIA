"""ARIA FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import health
from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("aria.startup", env=settings.aria_env, llm_provider=settings.llm_provider)
    yield
    log.info("aria.shutdown")


app = FastAPI(
    title="ARIA — Autonomous Revenue Intelligence Agent",
    version=__version__,
    description="Detects revenue at risk, reasons over root cause, and recovers it — with proof.",
    lifespan=lifespan,
)

# Dashboard (Vite dev server) origins. Tightened per-env in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {"service": "aria", "version": __version__, "docs": "/docs"}
