import json
import logging
import typing as t

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import JSONResponse
from pydantic import ValidationError

ERROR_APP_OP = (1409, "app operational error")
ERROR_UNKNOWN = (1500, "unknown error")

log = logging.getLogger("portsvc")


class BizException(Exception):
    def __init__(self, code: int | None = None, message: t.Any | None = None) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AppOpException(BizException):
    def __init__(self, message: t.Any | None = None) -> None:
        code = ERROR_APP_OP[0]
        message = message or ERROR_APP_OP[1]
        super().__init__(code, message)


def init_app(app: FastAPI) -> None:
    """Inits error handlers."""

    # HTTPException is handled by FastAPI's default handler, this one only sees unhandled errors
    @app.exception_handler(Exception)
    async def handle_exception(_: Request, e: Exception) -> JSONResponse:
        log.exception(e)
        return JSONResponse({"code": ERROR_UNKNOWN[0], "message": ERROR_UNKNOWN[1]}, status_code=500)

    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, e: ValidationError) -> JSONResponse:
        res = {
            "code": 1400,
            "message": e.errors(include_url=False, include_context=False, include_input=False),
        }
        log.error(json.dumps(res))
        return JSONResponse(res, status_code=400)

    @app.exception_handler(BizException)
    async def handle_biz_exception(_: Request, e: BizException) -> JSONResponse:
        res = {
            "code": e.code,
            "message": e.message,
        }
        log.error(json.dumps(res))
        return JSONResponse(res, status_code=409)
