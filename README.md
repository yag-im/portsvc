# portsvc

portsvc is a ports management service, used mainly for publishing new releases.

## release a new portsvc version

Inside a devcontainer:

    make lint
    make build

Outside of a devcontainer:

    make docker-build
    make docker-run
    make docker-pub TAG=0.0.1
