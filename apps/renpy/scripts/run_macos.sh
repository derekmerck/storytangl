#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)

if [ -z "${RENPY_SDK:-}" ]; then
    echo "Set RENPY_SDK to your Ren'Py SDK directory first."
    exit 1
fi

cd "$REPO_ROOT"
exec "$RENPY_SDK/renpy.app/Contents/MacOS/renpy" "$REPO_ROOT/apps/renpy/project" "$@"
