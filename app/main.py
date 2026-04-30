"""Team Task Manager – FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware

from app.core.rate_limit import limiter
from app.db.session import engine, Base
from app.api.v1 import auth, projects, tasks, analytics

# --------------- Logging ---------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")


# --------------- Lifespan ---------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Ensuring database tables exist…")
    Base.metadata.create_all(bind=engine)
    logger.info("Application started – %s v%s", settings.APP_NAME, settings.APP_VERSION)
    yield
    logger.info("Application shutting down …")


# --------------- App ---------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# --------------- Global Exception Handlers ---------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return 422 validation errors in the standard envelope."""
    errors = exc.errors()
    messages = "; ".join(
        f"{'.'.join(str(l) for l in e.get('loc', []))}: {e.get('msg', '')}"
        for e in errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": f"Validation error: {messages}", "data": None},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler so raw exceptions never leak to the client."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Internal server error", "data": None},
    )


from fastapi import HTTPException as _HTTPException


@app.exception_handler(_HTTPException)
async def http_exception_handler(request: Request, exc: _HTTPException):
    """Wrap FastAPI HTTPExceptions in the standard JSON envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail, "data": None},
    )


# --------------- Routers ---------------

app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


# --------------- Static Files ---------------

app.mount("/", StaticFiles(directory="static", html=True), name="static")
