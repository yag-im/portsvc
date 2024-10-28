from flask_restful import Api

from portsvc.api.port import (
    Publish,
    UpsertAppRelease,
)

api = Api()

# setup routing
api.add_resource(UpsertAppRelease, "/ports/apps/<igdb_slug>/releases/<app_release_uuid>")  # POST
api.add_resource(Publish, "/ports/apps/<igdb_slug>/releases/<app_release_uuid>/publish")  # POST
