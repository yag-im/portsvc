#!/usr/bin/env bash

mkdir -p /workspaces/portsvc/.vscode
cp /workspaces/portsvc/.devcontainer/vscode/* /workspaces/portsvc/.vscode

make bootstrap
