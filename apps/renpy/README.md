# StoryTangl Ren'Py Demo

This app is a small adapter proof of concept. It keeps StoryTangl in charge of
session lifecycle, traversal, and fragment production, then adapts typed
`RuntimeEnvelope` output into a Ren'Py-friendly turn model.

## What Is Included

- `apps/renpy/src/tangl/renpy/`
  A pure-Python bridge and adapter model.
- `apps/renpy/tests/`
  Python-first adapter and integration tests that run under the repo's normal
  `pytest` suite.
- `apps/renpy/project/game/`
  A minimal Ren'Py project that exercises the adapter manually.
- `worlds/renpy_demo/`
  A tiny VN-shaped demo world used by the bridge tests and the manual project.

## Running The Python Tests

```bash
poetry run pytest apps/renpy/tests
```

## Manual Ren'Py Smoke

Install a Ren'Py SDK separately. The SDK is intentionally not vendored and not
part of Poetry dependencies.

Run these from the repo root so StoryTangl picks up the checked-in
`settings.toml` and `worlds/` directory:

```bash
export RENPY_SDK=/path/to/renpy-sdk
"$RENPY_SDK/renpy.sh" apps/renpy/project lint
"$RENPY_SDK/renpy.sh" apps/renpy/project test
"$RENPY_SDK/renpy.sh" apps/renpy/project
```

The Ren'Py CLI is useful for local smoke coverage, but it stays outside default
CI for this demo.

