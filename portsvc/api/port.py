import yaml
from flask import (
    Response,
    request,
)
from flask_restful import Resource

from portsvc.biz.dto import (
    UpsertAppReleaseRequestDTO,
    UpsertAppReleaseResponseDTO,
)
from portsvc.biz.port import (
    publish,
    upsert_app_release,
)


class UpsertAppRelease(Resource):
    def post(self, igdb_slug: str, app_release_uuid: str) -> Response:
        """Adds new or updates existing app release."""
        descr = yaml.safe_load(request.get_data())["descr"]
        req: UpsertAppReleaseRequestDTO = UpsertAppReleaseRequestDTO.Schema().load(data=descr)
        res = upsert_app_release(igdb_slug, app_release_uuid, req)
        return UpsertAppReleaseResponseDTO.Schema().dump(res), 200


class Publish(Resource):
    def post(self, igdb_slug: str, app_release_uuid: str) -> Response:
        """Publishes app release, which includes uploading app bundle files, media assets etc"""
        publish(igdb_slug, app_release_uuid)
        return "", 200
