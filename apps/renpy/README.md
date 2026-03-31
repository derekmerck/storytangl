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

For the current mac demo, vendor the Python dependencies with a host Python
3.12 interpreter first. This keeps the Ren'Py side in-process without trying to
teach the embedded SDK Python how to install packages:

```bash
export RENPY_SDK=/path/to/renpy-sdk
python3.12 apps/renpy/scripts/vendor_python_packages.py
```

Then run the mac app-bundle executable from the repo root so StoryTangl picks
up the checked-in `settings.toml` and `worlds/` directory:

```bash
export RENPY_SDK=/path/to/renpy-sdk
apps/renpy/scripts/run_macos.sh lint
apps/renpy/scripts/run_macos.sh test
apps/renpy/scripts/run_macos.sh
```

`renpy.sh` in the 8.5.2 mac SDK bundle currently looks for unsuffixed binaries
under `lib/py3-mac-universal/`, while the actual executables live in
`renpy.app/Contents/MacOS/`, so the wrapper script above uses the working path.

The vendored `game/python-packages/` tree is ignored by git. Re-run the vendor
step whenever the StoryTangl dependency set changes.

The Ren'Py CLI is useful for local smoke coverage, but it stays outside default
CI for this demo.
