import logging

from fastapi import FastAPI

from portsvc.api import router
from portsvc.biz import (
    errors,
    log,
    sqldb,
)


def create_app() -> FastAPI:
    log.init()
    sqldb.init_engine()

    app = FastAPI(title="portsvc")
    app.include_router(router)
    errors.init_app(app)

    logging.getLogger("portsvc").info("app init completed")

    return app
