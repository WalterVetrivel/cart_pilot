"""Uniform error shape: {"error": {"code", "message"}} (SPEC §9)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def _body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return JSONResponse(_body("http_error", str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        # Field names and reasons only: echoing submitted values could leak tokens back out.
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ()) if p != 'body') or 'body'}: {e.get('msg', 'invalid')}"
            for e in exc.errors()
        )
        return JSONResponse(_body("validation_error", problems or "Invalid request."), status_code=422)
