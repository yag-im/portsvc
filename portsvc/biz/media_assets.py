import os
import tempfile
from pathlib import Path

import boto3
import requests
from sqlalchemy.orm import contains_eager

from portsvc.biz.dto import MediaAssets
from portsvc.biz.models import AppReleaseDAO

AWS_BUCKET_NAME = "cdn.yag.im"


# https://api-docs.igdb.com/#images
COVER_SIZE = "cover_big"
SCREENSHOT_SIZE = "screenshot_huge"


def upload(app_release_id: str) -> None:
    session = boto3.Session(profile_name="yag-prod")
    s3 = session.client("s3")

    app_release: AppReleaseDAO = (
        AppReleaseDAO.query.join(AppReleaseDAO.game)
        .options(contains_eager(AppReleaseDAO.game))
        .filter(AppReleaseDAO.uuid == app_release_id)
        .first()
    )

    if app_release.media_assets:
        localized_media_assets: MediaAssets = MediaAssets.Schema().load(data=app_release.media_assets)
        ports_data_media_dir = Path(os.environ["PORTS_DATA_MEDIA_DIR"])
        with tempfile.TemporaryDirectory() as td:
            img_name = f"{localized_media_assets.cover.image_id}.jpg"
            s3.upload_file(ports_data_media_dir / "covers" / img_name, AWS_BUCKET_NAME, f"covers/{img_name}")
            if localized_media_assets.screenshots:
                for ss in localized_media_assets.screenshots:
                    img_name = f"{ss.image_id}.jpg"
                    s3.upload_file(
                        ports_data_media_dir / "screenshots" / img_name, AWS_BUCKET_NAME, f"screenshots/{img_name}"
                    )

    game_media_assets: MediaAssets = MediaAssets.Schema().load(data=app_release.game.media_assets)
    with tempfile.TemporaryDirectory() as td:
        if not app_release.media_assets:
            # no localized cover - proceed with one from igdb
            tmp_img_name = f"{game_media_assets.cover.image_id}.jpg"
            tmp_img_path = Path(td) / tmp_img_name
            url = f"https://images.igdb.com/igdb/image/upload/t_{COVER_SIZE}/{tmp_img_name}"
            response = requests.get(url, stream=True, timeout=(3, 10))
            with open(tmp_img_path, "wb") as f:
                f.write(response.content)
            s3.upload_file(tmp_img_path, AWS_BUCKET_NAME, f"covers/{tmp_img_name}")

        if game_media_assets.screenshots:
            for ss in game_media_assets.screenshots:
                tmp_img_name = f"{ss.image_id}.jpg"
                tmp_img_path = Path(td) / tmp_img_name
                url = f"https://images.igdb.com/igdb/image/upload/t_{SCREENSHOT_SIZE}/{tmp_img_name}"
                response = requests.get(url, stream=True, timeout=(3, 10))
                with open(tmp_img_path, "wb") as f:
                    f.write(response.content)
                s3.upload_file(tmp_img_path, AWS_BUCKET_NAME, f"screenshots/{tmp_img_name}")
