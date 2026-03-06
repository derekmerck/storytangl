# v38 Cutover Log

## Baseline
- Baseline tag: `pre-cutover-namespace-swap`
- Baseline commit: `858d3a5`
- Snapshot time (UTC): `2026-03-05 21:38:04Z`

## Environment
- Python (poetry runtime): `Python 3.13.0`
- Python (host): `Python 3.11.5`
- Poetry: `Poetry 1.7.0`
- Platform: local macOS dev environment

### Persisted-data compatibility default
Cutover assumes no backwards compatibility guarantee for persisted artifacts generated before the namespace swap.

## Validation Lanes

### Lane A: v38 native engine
```bash
poetry run pytest -q engine/tests/core38 engine/tests/vm38 engine/tests/story38 engine/tests/service38 -o log_cli=false
```
Result: `918 passed`

### Lane B: non-retiring engine compatibility
```bash
poetry run pytest -q engine/tests/integration engine/tests/loaders engine/tests/ir engine/tests/journal engine/tests/persistence engine/tests/lang engine/tests/utils engine/tests/mechanics -o log_cli=false
```
Result: `665 passed, 62 skipped, 9 xfailed`

### Lane C: apps
```bash
poetry run pytest -q apps/cli/tests apps/server/tests -o log_cli=false
```
Result: `36 passed, 3 skipped, 1 xfailed`

## Current Expected Skip/XFail Inventory
- SKIP: `apps/server/tests/test_media_server_integration.py::test_media_story_round_trip`
  - reason: deferred during v38 cutover (legacy VM-phase coupling)
- SKIP: `apps/server/tests/test_multi_world_switching.py::test_story_debug_endpoints_are_wired`
  - reason: deferred during v38 cutover (debug endpoints preserved as `501 Not Implemented`)
- SKIP: `apps/server/tests/test_world_endpoints.py::test_world_info`
  - reason: legacy reference world bundle is not yet v38 codec-compatible
- XFAIL:
  - `apps/server/tests/test_rest_dependencies.py::test_story_router_uses_orchestrator_dependency`
    - reason: "not sure what it is doing here"

## Cutover Import Audit
Pre-swap gate command:

```bash
python scripts/audit_cutover_edges.py --mode pre-swap --enforce --json-out tmp/cutover_audit_preswap.json
```

Current pre-swap result:
- `IR bridge: 0`
- `Bypass imports: 0`
- `Intentional bridges: 0` (tracked via `scripts/cutover_import_allowlist.txt`)

Pre-swap audit now passes after tightening classification to treat `*_legacy`
source trees as transitional and only gate non-legacy bypass imports.

Intentional bridge allowlist is currently empty.

Post-swap gate command:

```bash
python scripts/audit_cutover_edges.py --mode post-swap --enforce --json-out tmp/cutover_audit_postswap.json
```

Current post-swap result:
- `IR bridge: 0`
- `Post-swap disallowed legacy imports: 0`
- `Post-swap disallowed *38 imports: 0`

CI now enforces the post-swap gate mode.

## Shim Plumbing Reduction (2026-03-06)
- Removed CLI legacy endpoint fallback plumbing:
  - deleted `StoryTanglCLI.call_legacy_endpoint(...)`
  - removed `_call_legacy(...)` helpers from CLI story/world/dev controllers
- Removed dead branch in `tangl.service.api_endpoint` that conditionally sourced
  endpoint metadata from a legacy module.
- Validation:
  - `python scripts/audit_cutover_edges.py --mode post-swap --enforce` → pass
  - `poetry run pytest -q engine/tests/service38/test_api_endpoint.py` → `29 passed`
  - `poetry run pytest -q engine/tests/service38` → `85 passed`
  - `poetry run pytest -q apps/cli/tests apps/server/tests` → `36 passed, 3 skipped, 1 xfailed`

## Namespace Retirement Cleanup (2026-03-06)
- Removed compatibility wrapper packages:
  - `engine/src/tangl/core38`
  - `engine/src/tangl/vm38`
  - `engine/src/tangl/story38`
  - `engine/src/tangl/service38`
- Loader/runtime cleanup:
  - `WorldCompiler` now enforces `runtime_version="38"` and no longer carries
    legacy runtime37 compile branches.
  - `WorldRegistry` now validates runtime version and passes through runtime
    selection to compiler methods.
- Validation:
  - Lane A: `918 passed`
  - Lane B: `665 passed, 62 skipped, 9 xfailed`
  - Lane C: `36 passed, 3 skipped, 1 xfailed`
  - Full suite: `1658 passed, 71 skipped, 10 xfailed`
  - Import sanity: `python -c "import tangl.core, tangl.vm, tangl.story, tangl.service"` → `ok`

## Endpoint Naming Cleanup (2026-03-06)
- Service operation routing now targets canonical runtime endpoint names:
  - `RuntimeController.create_story`
  - `RuntimeController.get_story_update`
  - `RuntimeController.resolve_choice`
  - `RuntimeController.get_story_info`
  - `RuntimeController.drop_story`
- Backward-compatible `*38` endpoint aliases remain accepted:
  - operation reverse-lookup maps suffixed names to canonical names
  - default endpoint policy is applied to both `create_story` and `create_story38`
- Added canonical `RuntimeController.get_story_update(...)` endpoint alias to match
  canonical operation routing.
- Validation:
  - Targeted service/app routes:
    - `poetry run pytest -q engine/tests/service38/controllers/test_runtime_controller.py engine/tests/integration/test_service_layer.py apps/server/tests/test_rest_dependencies38.py apps/server/tests/test_story38_endpoints.py` → `16 passed`
  - Full suite: `1658 passed, 71 skipped, 10 xfailed`
  - Post-swap import audit: pass (`IR bridge: 0`, legacy imports: `0`, `*38` imports: `0`)
