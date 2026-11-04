"""PhishGuard AI - FastAPI application entry point.

Run from the backend folder:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, error_body
from app.core.rate_limit import RateLimiter
from app.database.db import init_db
from app.services.ml_service import get_ml_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("phishguard")


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = RateLimiter(settings.rate_limit_per_minute)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        init_db()
        ml = get_ml_service()
        log.info("Model available: %s%s", ml.available, "" if ml.available else f" ({ml.error})")
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Static phishing / malicious-URL analysis. URLs submitted here are never opened or fetched.",
        lifespan=lifespan,
        redoc_url=None,
    )

    # --- guard middleware: body-size limit, rate limit, security headers -------------
    # (Added BEFORE CORS so CORS ends up outermost and also decorates 413/429 replies.)
    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.url.path.startswith("/api"):
            declared = request.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > settings.max_body_bytes:
                return JSONResponse(
                    status_code=413, content=error_body("payload_too_large", "Request body is too large.")
                )
            client_ip = request.client.host if request.client else "unknown"
            if not limiter.allow(client_ip):
                return JSONResponse(
                    status_code=429,
                    content=error_body("rate_limited", "Too many requests. Please wait a minute and try again."),
                    headers={"Retry-After": "60"},
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,  # explicit allow-list, never "*"
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["Content-Disposition"],
    )

    # --- error handling: one JSON shape, no stack traces or user input echoed back ----
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError):
        problems = []
        for err in exc.errors()[:5]:
            field = ".".join(str(p) for p in err.get("loc", []) if p != "body") or "request"
            problems.append(f"{field}: {err.get('msg', 'invalid value')}")
        return JSONResponse(
            status_code=422, content=error_body("validation_error", "Invalid request. " + "; ".join(problems))
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception):
        log.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "Something went wrong on the server. Check the backend log."),
        )

    app.include_router(api_router)
    return app


app = create_app()
