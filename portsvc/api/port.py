import typing as t

import yaml
from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from fastapi.exceptions import RequestValidationError
from fastapi_rfc9457 import InternalServerError
from fastapi_rfc9457.builtins import ValidationProblem
from fastapi_rfc9457.server import problems
from pydantic import ValidationError
from sqlalchemy.orm import Session

from portsvc.biz.dto import (
    UpsertAppReleaseRequestDTO,
    UpsertAppReleaseResponseDTO,
)
from portsvc.biz.errors import (
    AppNotFound,
    AppReleaseNotFound,
    CompanyNotFound,
    IgdbFailed,
    InconsistentData,
    MalformedBody,
    PlatformNotFound,
    S3Failed,
    UaLockPointerUnknown,
)
from portsvc.biz.port import (
    publish,
    upsert_app_release,
)
from portsvc.biz.sqldb import get_session

router = APIRouter(prefix="/ports/apps/{igdb_slug}/releases/{app_release_uuid}")

DbSession = t.Annotated[Session, Depends(get_session)]


async def upsert_request(request: Request) -> UpsertAppReleaseRequestDTO:
    try:
        body = yaml.safe_load(await request.body())
    except yaml.YAMLError as e:
        raise MalformedBody(error=" ".join(str(e).split())) from e
    try:
        return UpsertAppReleaseRequestDTO.model_validate(body)
    except ValidationError as e:
        # body is parsed manually, so its errors are reported the same way as FastAPI's request validation
        raise RequestValidationError(e.errors()) from e


# sync handlers run in a threadpool, biz layer is blocking (sqlalchemy, requests, boto3)
@router.post(
    "",
    operation_id="upsert_port",
    summary="Upsert app release",
    response_description="App release was created or updated, its UUID is returned",
    responses=problems(
        MalformedBody,
        AppNotFound,
        ValidationProblem,
        CompanyNotFound,
        PlatformNotFound,
        UaLockPointerUnknown,
        InconsistentData,
        InternalServerError,
        IgdbFailed,
    ),
)
def post_upsert_app_release(
    igdb_slug: str,
    app_release_uuid: str,
    req: t.Annotated[UpsertAppReleaseRequestDTO, Depends(upsert_request)],
    session: DbSession,
) -> UpsertAppReleaseResponseDTO:
    """Adds new or updates existing app release."""
    return upsert_app_release(session, igdb_slug, app_release_uuid, req)


@router.post(
    "/publish",
    operation_id="publish_port",
    status_code=204,
    summary="Publish app release",
    response_description="App release was published",
    responses=problems(AppReleaseNotFound, InternalServerError, S3Failed, IgdbFailed),
)
def post_publish(igdb_slug: str, app_release_uuid: str, session: DbSession) -> None:
    """Publishes app release, which includes uploading app bundle files, media assets etc"""
    publish(session, igdb_slug, app_release_uuid)
