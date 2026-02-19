# Core38 Docstring Drift Audit

## Scope
- Package: `engine/src/tangl/core38`
- Objective: correctness-first drift detection and docstring contract alignment
- Non-goal: runtime behavior changes

## Method
1. Parsed module/class/function docstrings across `core38` and compared against public callable surface.
2. Mapped documentation claims to `core38` tests in `engine/tests/core38`.
3. Ran doctests and unit tests to validate documentation truthfulness.
4. Applied targeted P0/P1 fixes and high-impact P2 method-level coverage in requested modules.

## Severity-Ranked Findings

### P0 (Correctness)

#### F-P0-001: `RuntimeOp` doctest example was not executable with `safe_builtins`
- File/line: `engine/src/tangl/core38/runtime_op.py:48`
- Drift type: wrong behavior in docs
- Current contract (before fix): example used `print(...)` inside `apply_all(...)`.
- Intended contract: examples must run under `safe_builtins`; `print` is unavailable.
- Legacy inspiration: examples in `engine/src/tangl/core/entity.py` prioritize runnable, assertion-oriented doctests.
- Status: fixed in this pass.

### P1 (Semantic Ambiguity / Stale Contracts)

#### F-P1-001: Dispatch module docstring referenced stale API names
- File/line: `engine/src/tangl/core38/dispatch.py:4`
- Drift type: stale name/path
- Current contract (before fix): referred to generic `on_task`/`do_task` and `Registry.add_item()`.
- Intended contract: explicit hook pairs (`on_init`, `do_init`, etc.) and `Registry.add/get/remove`.
- Legacy inspiration: explicit API sections in `engine/src/tangl/core/behavior/behavior_registry.py`.
- Status: fixed in this pass.

#### F-P1-002: `bases` cross-reference pointed to removed legacy module
- File/line: `engine/src/tangl/core38/bases.py:80`
- Drift type: stale name/path
- Current contract (before fix): `core.requirement` listed as current follow-on module.
- Intended contract: reference `vm38.provision.requirement` for requirement/provisioning semantics and `core38.*` for core surfaces.
- Legacy inspiration: module map discipline from `engine/src/tangl/core/registry.py` and `engine/src/tangl/core/graph/graph.py`.
- Status: fixed in this pass.

#### F-P1-003: `Behavior.sort_key` prose did not match tuple order
- File/line: `engine/src/tangl/core38/behavior.py:258`
- Drift type: wrong behavior in docs
- Current contract (before fix): claimed priority-first ordering.
- Intended contract: `dispatch_layer` first, then `priority`, then `wants_exact_kind`, then `seq`.
- Legacy inspiration: ordering contract clarity from enum docs in `engine/src/tangl/core/behavior/behavior.py`.
- Status: fixed in this pass.

#### F-P1-004: `merge_results` inline comment contradicted actual merge policy
- File/line: `engine/src/tangl/core38/behavior.py:165`
- Drift type: semantic contradiction
- Current contract (before fix): comment said early entries override late entries.
- Intended contract: later dict results override earlier ones (`ChainMap(*reversed(results))`).
- Legacy inspiration: reduction semantics and receipt prose in `engine/src/tangl/core/behavior/call_receipt.py`.
- Status: fixed in this pass.

### P2 (Coverage / Clarity)

#### F-P2-001: High-impact modules had missing public method docstrings
- Drift type: missing API explanation
- Modules prioritized by this pass: `runtime_op`, `dispatch`, `behavior`, `record`, `template`, `singleton`.
- Status: fixed in this pass (public-callable gaps reduced to zero for these modules).
- Legacy inspiration: class/API curation style in `engine/src/tangl/core/behavior/behavior_registry.py` and `engine/src/tangl/core/registry.py`.

#### F-P2-002: Remaining coverage hotspots outside requested target modules
- Drift type: missing API explanation
- Current hotspots (still open):
  - `engine/src/tangl/core38/bases.py`
  - `engine/src/tangl/core38/graph.py`
  - `engine/src/tangl/core38/ctx.py`
  - `engine/src/tangl/core38/token.py`
- Status: open (deferred by scope to keep momentum on correctness-first items).
- Legacy inspiration: detailed GraphItem/Graph surface docs in `engine/src/tangl/core/graph/graph.py`.

### P3 (Polish)

#### F-P3-001: Protocol method-level explanation depth remains uneven
- Drift type: polish
- Affected area: `RuntimeCtx` method semantics in `engine/src/tangl/core38/behavior.py`.
- Status: partially improved by module/class-level docs; method-level expansion deferred.

## Inventory Snapshot

### Pre-pass hotspot snapshot (captured)
- `runtime_op.py`: 100% missing public-callable docstrings
- `singleton.py`: 100%
- `template.py`: 95.2%
- `dispatch.py`: 92.9%
- `record.py`: 87.5%
- `behavior.py`: 85.7%

### Post-pass snapshot
- `runtime_op.py`: 0% missing
- `singleton.py`: 0%
- `template.py`: 0%
- `dispatch.py`: 0%
- `record.py`: 0%
- `behavior.py`: 33.3% (residual primarily protocol/helper methods)

## Rewrite Snippet Pack (P0/P1)

### S-P0-001 (`runtime_op.py` doctest-safe example)
```python
>>> RuntimeOp.apply_all("abc = abc + 1", "abc = abc * 2", ns={"abc": 123})
{'abc': 248}
```

### S-P1-001 (`dispatch.py` module contract language)
```text
Default global dispatch registry and explicit hook pairs for core38 lifecycle events.
...
- `on_create` / `do_create`
- `on_init` / `do_init`
- `on_add_item` / `do_add_item`
...
```

### S-P1-002 (`bases.py` where-to-look references)
```text
- `core38.selector` for matching.
- `vm38.provision.requirement` for satisfaction and provisioning contracts.
- `core38.registry` for registry ownership and grouping.
```

### S-P1-003 (`behavior.py` sort-key semantics)
```text
Sorts by:
  - layer: global -> local
  - priority: low -> high
  - wants_exact_kind: False then True
  - registration seq: earlier -> later
```

### S-P1-004 (`behavior.py` dict-merge policy note)
```python
return ChainMap(*reversed(results))  # later dict values override earlier ones
```

## Optional P2 Snippet Set (Prioritized)
1. `engine/src/tangl/core38/graph.py`: add concise docs for typed find helpers and `GraphItem.graph` alias.
2. `engine/src/tangl/core38/ctx.py`: document `get_ctx`/`using_ctx` runtime contract explicitly.
3. `engine/src/tangl/core38/token.py`: add method docs for `reference_singleton`, factory helpers, and wrapper semantics.
4. `engine/src/tangl/core38/bases.py`: add concise docs to `HasIdentity` helper methods (`get_identifiers`, `has_identifier`, `id_hash`).

## Reusable Rubric for vm38/story38/service38

1. **Executable examples**: every doctest must run under real safety/runtime constraints.
2. **Name fidelity**: doc names must match current callable/API names exactly.
3. **Ordering fidelity**: prose ordering must match real tuple/sort behavior.
4. **Aggregation fidelity**: reduction semantics must match actual fold functions.
5. **Context contract clarity**: minimal required protocol methods are explicit.
6. **Boundary clarity**: clearly separate mechanism (core/vm) vs policy (story/service).
7. **Layer references current**: no stale module references from pre-refactor names.
8. **Public method coverage**: non-trivial public methods have one-sentence contract docs.
9. **Cross-layer pointers**: each module has actionable `See Also` links to current layer peers.
10. **Truthfulness gate**: docs pass doctests and do not contradict package tests.

## Validation
- Doctests: `poetry run pytest --doctest-modules engine/src/tangl/core38 -q`
- Core38 tests: `poetry run pytest engine/tests/core38 -q`

Both were run after this pass and are green.
