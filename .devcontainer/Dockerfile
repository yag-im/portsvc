ARG DEBIAN_VER=trixie

FROM mcr.microsoft.com/devcontainers/python:3-3.14-${DEBIAN_VER}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
      7zip
