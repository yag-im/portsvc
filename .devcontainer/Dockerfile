ARG DEBIAN_VER=bookworm

FROM mcr.microsoft.com/devcontainers/python:1-3.11-${DEBIAN_VER}

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
      7zip \
      iputils-ping
