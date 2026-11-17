"""Errors are returned as RFC 9457 problem details (application/problem+json) by fastapi-rfc9457."""

import inspect
import logging
import typing as t
from collections.abc import (
    Awaitable,
    Callable,
    Iterator,
)
from contextlib import contextmanager

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi_rfc9457 import Problem
from fastapi_rfc9457.server import add_problem_handlers
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

log = logging.getLogger("portsvc")


class PortsvcProblem(Problem, abstract=True):
    """Base problem which fills in detail from a template using the problem's extension members."""

    detail_template: t.ClassVar[str | None] = None

    def __post_init__(self) -> None:
        if self.detail is None and self.detail_template:
            self.detail = self.detail_template.format(**{f: getattr(self, f) for f in self.__dataclass_fields__})


# "type" is set explicitly, so renaming a class does not change the identifier clients rely on
class MalformedBody(PortsvcProblem):
    """Request body is not a valid YAML."""

    type = "malformed-body"
    title = "Malformed request body"
    status = 400
    detail_template = "Request body is not a valid YAML, see error for parser message"
    error: str


class AppNotFound(PortsvcProblem):
    """App with given IGDB slug exists neither in DB nor on IGDB."""

    type = "app-not-found"
    title = "App not found"
    status = 404
    detail_template = "App not found: {igdb_slug}"
    igdb_slug: str


class AppReleaseNotFound(PortsvcProblem):
    """No app release with given UUID belongs to app with given IGDB slug."""

    type = "app-release-not-found"
    title = "App release not found"
    status = 404
    detail_template = "App release not found: {igdb_slug}/{app_release_uuid}"
    igdb_slug: str
    app_release_uuid: str


class CompanyNotFound(PortsvcProblem):
    """Publisher from descriptor is not in DB."""

    type = "company-not-found"
    title = "Company not found"
    status = 422
    detail_template = "Company not found: {publisher}"
    publisher: str


class PlatformNotFound(PortsvcProblem):
    """Platform from descriptor is not in DB."""

    type = "platform-not-found"
    title = "Platform not found"
    status = 422
    detail_template = "Platform not found: {platform}"
    platform: str


class UaLockPointerUnknown(PortsvcProblem):
    """UA lock pointer state is not set and cannot be derived from runner/installer."""

    type = "ua-lock-pointer-unknown"
    title = "UA lock pointer state cannot be determined"
    status = 422
    detail_template = (
        "Cannot determine UA lock pointer state for runner: {runner}, set descr.reqs.ua.lock_pointer explicitly"
    )
    runner: str


class InconsistentData(PortsvcProblem):
    """IGDB slug matches more than one app in DB."""

    type = "inconsistent-data"
    title = "Inconsistent app data"
    status = 500
    detail_template = "Multiple apps match IGDB slug: {igdb_slug}, please investigate"
    igdb_slug: str


class IgdbFailed(PortsvcProblem):
    """IGDB is unreachable, returned an error or rejected credentials."""

    type = "igdb-failed"
    title = "IGDB request failed"
    status = 502


class S3Failed(PortsvcProblem):
    """S3 is unreachable or rejected the upload."""

    type = "s3-failed"
    title = "S3 request failed"
    status = 502


@contextmanager
def upstream_errors(problem: type[Problem], *exc_types: type[Exception]) -> Iterator[None]:
    """Converts given exceptions raised by an external service client into given problem."""
    try:
        yield
    except exc_types as e:
        log.exception(problem.title)
        raise problem() from e


Handler = Callable[[Request, t.Any], Response | Awaitable[Response]]

_LOGGED_ATTR = "_portsvc_logged"


class _SkipLoggedErrors(logging.Filter):
    """Drops server's duplicate traceback of an error already logged by our handler.

    Starlette re-raises unhandled errors after the handler responds, so uvicorn logs them again.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        exc = record.exc_info[1] if record.exc_info else None
        return not getattr(exc, _LOGGED_ATTR, False)


_skip_logged_errors = _SkipLoggedErrors()


def _logged(handler: Handler, with_traceback: bool = False) -> Handler:
    """Wraps library's handler to log every problem response it produces."""

    async def wrapper(request: Request, e: Exception) -> Response:
        if with_traceback:
            log.exception(e)
            setattr(e, _LOGGED_ATTR, True)
        res = handler(request, e)
        if inspect.isawaitable(res):
            res = await res
        log.error(bytes(res.body).decode())
        return res

    return wrapper


_ALWAYS_SENT_MEMBERS = ("type", "title", "status")


def _fix_openapi(schema: dict[str, t.Any]) -> None:
    """Aligns library-generated problem schemas with what is actually sent."""
    components = schema.get("components", {}).get("schemas", {})
    for component in components.values():
        if set(_ALWAYS_SENT_MEMBERS) <= component.get("properties", {}).keys():
            component["required"] = list(dict.fromkeys([*_ALWAYS_SENT_MEMBERS, *component.get("required", [])]))
    # strip_debug=True never sends offending input of validation errors
    if invalid_param := components.get("InvalidParam"):
        invalid_param.get("properties", {}).pop("input", None)
        invalid_param["description"] = "One field-level validation failure."
    for path_item in schema.get("paths", {}).values():
        for op in path_item.values():
            for res in op.get("responses", {}).values():
                for media in res.get("content", {}).values():
                    for example in media.get("examples", {}).values():
                        for error in example.get("value", {}).get("errors", []):
                            error.pop("input", None)


def init_app(app: FastAPI) -> None:
    """Inits error handlers."""
    add_problem_handlers(app, strip_debug=True)
    for exc_type in (Problem, RequestValidationError):
        app.add_exception_handler(exc_type, _logged(app.exception_handlers[exc_type]))
    app.add_exception_handler(Exception, _logged(app.exception_handlers[Exception], with_traceback=True))
    logging.getLogger("uvicorn.error").addFilter(_skip_logged_errors)

    # framework errors (e.g. unknown route 404, 405) keep FastAPI's default format
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, e: StarletteHTTPException) -> Response:
        return await http_exception_handler(request, e)

    gen_openapi = app.openapi  # library's wrapper, builds problem responses and components

    def openapi() -> dict[str, t.Any]:
        if app.openapi_schema is None:
            _fix_openapi(gen_openapi())
        return t.cast(dict[str, t.Any], app.openapi_schema)

    app.openapi = openapi  # type: ignore[method-assign]
