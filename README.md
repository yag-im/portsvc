# portsvc

`portsvc` is a `ports` management helper service, primarily used for publishing new app releases. The current design is
flaky and requires refactoring.

The service provides two endpoints:

*Add new app release*: should be called to add a new app record into the SQL database.

*Publish new app release*: propagates the new app's data (covers, screenshots) into the CDN.

The first endpoint is called twice from [ports](https://github.com/yag-im/ports): first to update the local SQL database
for testing, and then using the production `portsvc`'s URL to publish the new app release to the production environment.

# Local development

Before starting a `devcontainer`:

Mount appstor disk at:

    /mnt/appstor

Make sure it contains a `media` folder with following structure:

    media/
        covers/
        screenshots/

Create following files:

.devcontainer/.env

    # gunicorn (see runtime/bin/cmd.sh for default values)
    GUNICORN_NUM_WORKERS=1
    GUNICORN_NUM_THREADS=10
    GUNICORN_TIMEOUT=3600

    # service
    LISTEN_IP=0.0.0.0
    LISTEN_PORT=80

    # otel
    OTEL_TRACE_ENABLED=false

    # flask
    FLASK_DEBUG=true
    FLASK_ENV=development
    FLASK_PROPAGATE_EXCEPTIONS=true

    FLASK_SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": true, "pool_size": 10, "pool_recycle": 120}
    #FLASK_SQLALCHEMY_TRACK_MODIFICATIONS=true
    SQLDB_DBNAME=yag
    SQLDB_HOST=sqldb.yag.dc
    SQLDB_PORT=5432
    SQLDB_USERNAME=portsvc

    # for uploading covers and screenshots from local appstor data directory to S3
    APPSTOR_MEDIA_DIR=/mnt/appstor/media

.devcontainer/secrets.env

    SQLDB_PASSWORD=PASTE-PORTSVC-SQL-DB-PASSWORD-HERE
