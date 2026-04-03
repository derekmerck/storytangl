#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)

if [ -z "${RENPY_SDK:-}" ]; then
    echo "Set RENPY_SDK to your Ren'Py SDK directory first."
    exit 1
fi

if [ -x "$RENPY_SDK/renpy-local.app/Contents/MacOS/renpy" ]; then
    RENPY_BIN="$RENPY_SDK/renpy-local.app/Contents/MacOS/renpy"
else
    RENPY_BIN="$RENPY_SDK/renpy.app/Contents/MacOS/renpy"
fi

cd "$REPO_ROOT"
exec "$RENPY_BIN" "$REPO_ROOT/apps/renpy/project" "$@"
