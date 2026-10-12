import logging


def init() -> None:
    # log setup
    # TODO: make log_level configurable
    log_level = logging.DEBUG

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s.%(msecs)03d] [%(name)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    app_log = logging.getLogger("portsvc")
    app_log.handlers.clear()
    app_log.addHandler(handler)
    app_log.setLevel(log_level)
    app_log.propagate = False

    root_log = logging.getLogger()
    root_log.handlers.clear()
    root_log.addHandler(handler)
    root_log.setLevel(log_level)
    root_log.propagate = False

    # talkative modules:
    logging.getLogger("urllib3").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)
