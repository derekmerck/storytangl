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
Result: `37 passed, 2 skipped, 1 xfailed`

## Current Expected Skip/XFail Inventory
- SKIP: `apps/server/tests/test_media_server_integration.py::test_media_story_round_trip`
  - reason: deferred during v38 cutover (legacy VM-phase coupling)
- SKIP: `apps/server/tests/test_multi_world_switching.py::test_story_debug_endpoints_are_wired`
  - reason: deferred during v38 cutover (debug endpoints preserved as `501 Not Implemented`)
- XFAIL:
  - `apps/server/tests/test_rest_dependencies.py::test_story_router_uses_orchestrator_dependency`
    - reason: "not sure what it is doing here"

## Cutover Import Audit
Pre-swap gate command:

```bash
python scripts/audit_cutover_edges.py --mode pre-swap --enforce --json-out tmp/cutover_audit_preswap.json
```

Current result:
- `IR bridge: 0`
- `Bypass imports: 0`
- `Intentional bridges: 34` (tracked via `scripts/cutover_import_allowlist.txt`)
