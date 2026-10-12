import logging
from typing import Any

from sqlalchemy import null
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from portsvc.biz.dto import (
    PortDescr,
    UpsertAppReleaseRequestDTO,
    UpsertAppReleaseResponseDTO,
)
from portsvc.biz.errors import AppOpException
from portsvc.biz.media_assets import upload as upload_media_assets
from portsvc.biz.models import (
    AppCompanyDAO,
    AppDAO,
    AppPlatformDAO,
    AppReleaseDAO,
)
from portsvc.biz.scrapers.igdb.index import get_game_by_slug

log = logging.getLogger("portsvc")


def try_to_fetch_game_from_igdb(session: Session, igdb_slug: str, upd_params: dict) -> bool:
    igdb_game = get_game_by_slug(igdb_slug)
    if not igdb_game:
        return False

    # alternative_names
    alternative_names = igdb_game.get("alternative_names", None)
    if alternative_names:
        alternative_names = [an["name"] for an in alternative_names]

    # esrb_rating
    esrb_rating = None
    age_ratings = igdb_game.get("age_ratings", None)
    if age_ratings:
        for ar in age_ratings:
            if ar.get("category", None) == 1:
                esrb_rating = ar["rating"]
                break

    # media_assets
    screenshots = igdb_game.get("screenshots", [])
    if screenshots:
        screenshots = [
            {
                "height": s.get("height", None),
                "width": s.get("width", None),
                "image_id": s["image_id"],
            }
            for s in screenshots
        ]
    cover = {"image_id": igdb_game["cover"]["image_id"]} if "cover" in igdb_game else None
    media_assets = {"screenshots": screenshots, "cover": cover}

    genres = igdb_game.get("genres", None)
    if genres:
        genres = [str(g["id"]) for g in genres]

    values = {
        "alternative_names": alternative_names,
        "companies": igdb_game.get("involved_companies", None),
        "esrb_rating": esrb_rating,
        "genres": genres,
        "long_descr": igdb_game.get("storyline", None),
        "media_assets": media_assets,
        "name": igdb_game.get("name"),
        "platforms": igdb_game.get("platforms", None),
        "short_descr": igdb_game.get("summary", None),
        "igdb": {"id": igdb_game["id"], "slug": igdb_game["slug"], "similar_ids": igdb_game.get("similar_games", [])},
    }
    values |= upd_params
    # drop all None values from dict because None values for JSONB columns go as "null" strings instead of None
    values = {k: v for k, v in values.items() if v is not None}
    sql_cmd = insert(AppDAO).values(values)
    session.execute(sql_cmd)
    session.commit()
    return True


def get_ua_lock_pointer_state(req: UpsertAppReleaseRequestDTO) -> bool:
    port_descr = req.descr
    port_installer = req.installer
    runner_name = port_descr.runner.name.lower()
    if runner_name == "scummvm":
        return False
    elif runner_name == "retroarch":
        for t in port_installer.tasks:
            if "retroarch" in t:
                tasks = t["retroarch"].get("tasks", [])
                for task in tasks:
                    if "gen_run_script" in task:
                        flavor = task["gen_run_script"].get("core", "default")
                        if flavor == "fuse":
                            return False
                        elif flavor == "same_cdi":
                            return True
                        elif flavor == "genesis_plus_gx":
                            return True
                        elif flavor == "puae":
                            return True
                        elif flavor == "mame":
                            return True
    elif runner_name == "dosbox-staging":
        return True
    elif runner_name == "dosbox-x":
        for t in port_installer.tasks:
            if "dosbox" in t:
                flavor = t["dosbox"].get("flavor", None)
                if flavor == "WIN311":
                    return False
                else:
                    return True
    elif runner_name == "qemu":
        return False
    elif runner_name == "wine":
        return False
    elif runner_name == "dosbox":
        return True
    raise ValueError(f"Cannot determine UA lock pointer state based on provided data: {req}")


def upsert_app_release(
    session: Session, igdb_slug: str, app_release_uuid: str, req: UpsertAppReleaseRequestDTO
) -> UpsertAppReleaseResponseDTO:
    """Upserts app release."""
    port_descr = req.descr
    if port_descr.reqs.ua is None or port_descr.reqs.ua.lock_pointer is None:
        if port_descr.reqs.ua is None:
            port_descr.reqs.ua = PortDescr.Reqs.Ua(lock_pointer=get_ua_lock_pointer_state(req))
        else:
            port_descr.reqs.ua.lock_pointer = get_ua_lock_pointer_state(req)

    # upserting "app" table parts first
    upd_params: dict[Any, Any] = {"refs": port_descr.refs.model_dump()}
    if port_descr.esrb_rating:
        upd_params["esrb_rating"] = port_descr.esrb_rating
    if port_descr.tags:
        upd_params["tags"] = port_descr.tags
    rows_updated = session.query(AppDAO).filter(AppDAO.igdb["slug"].astext == igdb_slug).update(upd_params)
    if rows_updated == 0:
        if not try_to_fetch_game_from_igdb(session, igdb_slug, upd_params):
            raise AppOpException(message="App not found")
    elif rows_updated > 1:
        raise AppOpException(message="Multiple apps touched, this is unexpected, please investigate")

    # upserting "app_release" table parts
    app = session.query(AppDAO).filter(AppDAO.igdb["slug"].astext == igdb_slug).first()
    if app is None:
        raise AppOpException(message="App not found")
    company = session.query(AppCompanyDAO).filter(AppCompanyDAO.name == port_descr.publisher).first()
    if company is None:
        raise AppOpException(message=f"Company not found: {port_descr.publisher}")
    platform = session.query(AppPlatformDAO).filter(AppPlatformDAO.slug == port_descr.platform).first()
    if platform is None:
        raise AppOpException(message=f"Platform not found: {port_descr.platform}")
    values = {
        "app_reqs": port_descr.reqs.model_dump(),
        "companies": [{"id": company.id, "developer": False, "porting": False, "publisher": True, "supporting": False}],
        "distro": port_descr.distro.model_dump(),
        "game_id": app.id,
        "is_visible": port_descr.is_visible,
        "lang": port_descr.lang,
        "media_assets": (port_descr.media_assets.model_dump() if port_descr.media_assets else null()),
        "name": port_descr.name,
        "platform_id": platform.id,
        "runner": port_descr.runner.model_dump(),
        "uuid": app_release_uuid,
        "year_released": port_descr.year_released,
    }
    sql_cmd = insert(AppReleaseDAO).values(values)
    sql_cmd = sql_cmd.on_conflict_do_update(
        index_elements=[AppReleaseDAO.uuid],
        index_where=(AppReleaseDAO.uuid == app_release_uuid),
        set_=values,
    )
    session.execute(sql_cmd)
    session.commit()

    return UpsertAppReleaseResponseDTO(app_release_uuid=app_release_uuid)


def publish(session: Session, igdb_slug: str, app_release_id: str) -> None:
    log.debug("publishing app: %s, app_release_id: %s", igdb_slug, app_release_id)
    upload_media_assets(session, app_release_id)
