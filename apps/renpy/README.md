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

## Status

This adapter is a demo and interoperability proof of concept.

- It demonstrates that StoryTangl can drive a Ren'Py client through the normal
  service/journal surface.
- It is useful as an expressiveness demo, a technical compatibility check, and
  a reference pattern for other client adapters.
- It is not a supported bridge product at this point. Save/load integration,
  remote transport, richer media handling, and packaged cross-platform
  distribution are all intentionally out of scope for the current demo.

## How It Works

The arrangement is intentionally close to the CLI:

1. StoryTangl stays responsible for story lifecycle, traversal, and fragment
   production through `ServiceManager`.
2. `RenPySessionBridge` starts a story, keeps the active `ledger_id`, and
   converts typed journal fragments into a tiny Ren'Py turn model.
3. Media fragments are dereferenced through the service-layer media helpers
   using a Ren'Py-friendly `MediaRenderProfile` with passthrough file paths and
   fallback handling.
4. The Ren'Py client stays small. `game/script.rpy` hosts a tiny game loop that
   starts the story, applies media ops, says lines, presents choices, resolves
   the selected choice, and repeats until the envelope ends.

That keeps the bridge at the adapter layer. The engine does not learn a
Ren'Py-specific fragment contract, and the client consumes presentation rather
than engine semantics.

## Running The Python Tests

```bash
poetry run pytest apps/renpy/tests
```

## Manual Ren'Py Smoke

Install a Ren'Py SDK separately. The SDK is intentionally not vendored and not
part of Poetry dependencies.

For the current mac demo, vendor the Python dependencies with a host Python
3.12 interpreter first. The helper copies the host environment's installed
third-party packages into `game/python-packages/` and writes a local `.pth`
file so Ren'Py imports StoryTangl itself directly from this checkout:

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
If you keep an ad-hoc re-signed `renpy-local.app` beside the stock bundle to
work around macOS library validation for vendored native extensions, the
wrapper prefers that copy automatically.

The vendored `game/python-packages/` tree is ignored by git. Re-run the vendor
step whenever the local dependency environment changes.

For very trimmed runtimes, file-backed shelved caches can be disabled globally
with `service.caches.shelved = false`. The Ren'Py demo does not require those
caches for correctness, and `game/script.rpy` disables them by default for the
demo process unless you override that explicitly.

The Ren'Py CLI is useful for local smoke coverage, but it stays outside default
CI for this demo.
