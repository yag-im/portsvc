import typing as t

import yaml
from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from sqlalchemy.orm import Session

from portsvc.biz.dto import (
    UpsertAppReleaseRequestDTO,
    UpsertAppReleaseResponseDTO,
)
from portsvc.biz.port import (
    publish,
    upsert_app_release,
)
from portsvc.biz.sqldb import get_session

router = APIRouter(prefix="/ports/apps/{igdb_slug}/releases/{app_release_uuid}")

DbSession = t.Annotated[Session, Depends(get_session)]


async def upsert_request(request: Request) -> UpsertAppReleaseRequestDTO:
    return UpsertAppReleaseRequestDTO.model_validate(yaml.safe_load(await request.body()))


# sync handlers run in a threadpool, biz layer is blocking (sqlalchemy, requests, boto3)
@router.post("")
def post_upsert_app_release(
    igdb_slug: str,
    app_release_uuid: str,
    req: t.Annotated[UpsertAppReleaseRequestDTO, Depends(upsert_request)],
    session: DbSession,
) -> UpsertAppReleaseResponseDTO:
    """Adds new or updates existing app release."""
    return upsert_app_release(session, igdb_slug, app_release_uuid, req)


@router.post("/publish")
def post_publish(igdb_slug: str, app_release_uuid: str, session: DbSession) -> str:
    """Publishes app release, which includes uploading app bundle files, media assets etc"""
    publish(session, igdb_slug, app_release_uuid)
    return ""
