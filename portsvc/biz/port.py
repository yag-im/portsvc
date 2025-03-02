import logging

from sqlalchemy import null
from sqlalchemy.dialects.postgresql import insert

from portsvc.biz.dto import (
    MediaAssets,
    UpsertAppReleaseRequestDTO,
)
from portsvc.biz.errors import AppOpException
from portsvc.biz.media_assets import upload as upload_media_assets
from portsvc.biz.models import (
    AppCompanyDAO,
    AppDAO,
    AppPlatformDAO,
    AppReleaseDAO,
)
from portsvc.biz.sqldb import sqldb

log = logging.getLogger("portsvc")


def upsert_app_release(igdb_slug: str, app_release_uuid: str, req: UpsertAppReleaseRequestDTO) -> dict:
    """Upserts app release."""
    # upserting "app" table parts first
    upd_params = {"refs": UpsertAppReleaseRequestDTO.Refs.Schema().dump(req.refs)}
    if req.esrb_rating:
        upd_params["esrb_rating"] = req.esrb_rating
    rows_updated = sqldb.session.query(AppDAO).filter(AppDAO.igdb["slug"].astext == igdb_slug).update(upd_params)
    if rows_updated == 0:
        raise AppOpException(message="App not found")
    elif rows_updated > 1:
        raise AppOpException(message="Multiple apps touched, this is unexpected, please investigate")

    # upserting "app_release" table parts
    app: AppDAO = sqldb.session.query(AppDAO).filter(AppDAO.igdb["slug"].astext == igdb_slug).first()
    company: AppCompanyDAO = sqldb.session.query(AppCompanyDAO).filter(AppCompanyDAO.name == req.publisher).first()
    platform: AppPlatformDAO = sqldb.session.query(AppPlatformDAO).filter(AppPlatformDAO.slug == req.platform).first()
    values = {
        "app_reqs": UpsertAppReleaseRequestDTO.Reqs.Schema().dump(req.reqs),
        "companies": [{"id": company.id, "developer": False, "porting": False, "publisher": True, "supporting": False}],
        "distro": UpsertAppReleaseRequestDTO.Distro.Schema().dump(req.distro),
        "game_id": app.id,
        "is_visible": req.is_visible,
        "lang": req.lang,
        "media_assets": (MediaAssets.Schema().dump(req.media_assets) if req.media_assets else null()),
        "name": req.name,
        "platform_id": platform.id,
        "runner": UpsertAppReleaseRequestDTO.Runner.Schema().dump(req.runner),
        "ts_added": req.ts_added,
        "uuid": app_release_uuid,
        "year_released": req.year_released,
    }
    sql_cmd = insert(AppReleaseDAO).values(values)
    sql_cmd = sql_cmd.on_conflict_do_update(
        index_elements=[AppReleaseDAO.uuid],
        index_where=(AppReleaseDAO.uuid == app_release_uuid),
        set_=values,
    )
    sqldb.session.execute(sql_cmd)
    sqldb.session.commit()

    return {"app_release_uuid": app_release_uuid}


def publish(igdb_slug: str, app_release_id: str) -> None:
    log.debug("publishing app: %s, app_release_id: %s", igdb_slug, app_release_id)
    upload_media_assets(app_release_id)
