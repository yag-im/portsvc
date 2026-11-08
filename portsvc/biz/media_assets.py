import os
import tempfile
import typing as t
from pathlib import Path

import boto3
import requests
from boto3.exceptions import Boto3Error
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from sqlalchemy.orm import (
    Session,
    contains_eager,
)

from portsvc.biz.dto import MediaAssets
from portsvc.biz.errors import (
    AppReleaseNotFound,
    IgdbFailed,
    S3Failed,
    upstream_errors,
)
from portsvc.biz.models import (
    AppDAO,
    AppReleaseDAO,
)

AWS_BUCKET_NAME = "cdn.yag.im"


# https://api-docs.igdb.com/#images
COVER_SIZE = "cover_big"
SCREENSHOT_SIZE = "screenshot_huge"


def upload(session: Session, igdb_slug: str, app_release_id: str) -> None:
    aws_session = boto3.Session(profile_name="yag-prod")
    s3 = aws_session.client("s3")

    app_release: AppReleaseDAO | None = (
        session.query(AppReleaseDAO)
        .join(AppReleaseDAO.game)
        .options(contains_eager(AppReleaseDAO.game))
        .filter(AppReleaseDAO.uuid == app_release_id, AppDAO.igdb["slug"].astext == igdb_slug)
        .first()
    )
    if app_release is None:
        raise AppReleaseNotFound(igdb_slug=igdb_slug, app_release_uuid=app_release_id)

    with (
        upstream_errors(S3Failed, BotoCoreError, ClientError, Boto3Error),
        upstream_errors(IgdbFailed, requests.RequestException),
    ):
        _upload(s3, app_release)


def _upload(s3: t.Any, app_release: AppReleaseDAO) -> None:
    if app_release.media_assets:
        localized_media_assets = MediaAssets.model_validate(app_release.media_assets)
        ports_data_media_dir = Path(os.environ["PORTS_DATA_MEDIA_DIR"])

        with tempfile.TemporaryDirectory() as td:
            if localized_media_assets.cover:
                img_name = f"{localized_media_assets.cover.image_id}.jpg"
                s3.upload_file(ports_data_media_dir / "covers" / img_name, AWS_BUCKET_NAME, f"covers/{img_name}")
            if localized_media_assets.screenshots:
                for ss in localized_media_assets.screenshots:
                    img_name = f"{ss.image_id}.jpg"
                    s3.upload_file(
                        ports_data_media_dir / "screenshots" / img_name, AWS_BUCKET_NAME, f"screenshots/{img_name}"
                    )

    game_media_assets = MediaAssets.model_validate(app_release.game.media_assets or {})
    with tempfile.TemporaryDirectory() as td:
        if not app_release.media_assets and game_media_assets.cover:
            # no localized cover - proceed with one from igdb
            tmp_img_name = f"{game_media_assets.cover.image_id}.jpg"
            tmp_img_path = Path(td) / tmp_img_name
            url = f"https://images.igdb.com/igdb/image/upload/t_{COVER_SIZE}/{tmp_img_name}"
            response = requests.get(url, stream=True, timeout=(3, 10))
            response.raise_for_status()
            with open(tmp_img_path, "wb") as f:
                f.write(response.content)
            s3.upload_file(tmp_img_path, AWS_BUCKET_NAME, f"covers/{tmp_img_name}")

        if game_media_assets.screenshots:
            for ss in game_media_assets.screenshots:
                tmp_img_name = f"{ss.image_id}.jpg"
                tmp_img_path = Path(td) / tmp_img_name
                url = f"https://images.igdb.com/igdb/image/upload/t_{SCREENSHOT_SIZE}/{tmp_img_name}"
                response = requests.get(url, stream=True, timeout=(3, 10))
                response.raise_for_status()
                with open(tmp_img_path, "wb") as f:
                    f.write(response.content)
                s3.upload_file(tmp_img_path, AWS_BUCKET_NAME, f"screenshots/{tmp_img_name}")
