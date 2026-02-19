# VM38 Docstring Drift Audit

## Scope
- Package: `engine/src/tangl/vm38`
- Comparison baseline: `engine/src/tangl/vm`
- Objective: correctness-first doc drift detection and alignment plan for refactored vm surface
- Non-goal: runtime behavior/API changes

## Method
1. Parsed vm38 module/class/function docstrings and public callable coverage.
2. Compared high-impact vm38 modules against legacy vm docs for reusable patterns.
3. Mapped doc claims to vm38 tests in `engine/tests/vm38`.
4. Ran doctests and vm38 test suite as truth gates.

## Validation Snapshot
- `poetry run pytest --doctest-modules engine/src/tangl/vm38 -q` -> 12 passed
- `poetry run pytest engine/tests/vm38 -q` -> 220 passed

## Coverage Snapshot
- Public callable doc coverage (vm38): **77/177 missing (43.5%)**
- Module doc coverage (vm38): **11/22 modules missing module docstrings**

Top vm38 hotspots by missing public callable docstrings:
- `engine/src/tangl/vm38/provision/resolver.py` -> 12/12 missing (100.0%)
- `engine/src/tangl/vm38/provision/provisioner.py` -> 15/18 missing (83.3%)
- `engine/src/tangl/vm38/provision/requirement.py` -> 11/17 missing (64.7%)
- `engine/src/tangl/vm38/dispatch.py` -> 9/13 missing (69.2%)
- `engine/src/tangl/vm38/replay/patch.py` -> 5/6 missing (83.3%)

Legacy-vs-vm38 contrast (selected):
- `engine/src/tangl/vm/__init__.py` has a strong conceptual map; vm38 previously lacked this and is now aligned in `engine/src/tangl/vm38/__init__.py`.
- `engine/src/tangl/vm/provision/resolver.py` is fully documented at callable level; `engine/src/tangl/vm38/provision/resolver.py` is entirely undocumented at callable level.
- vm38 `runtime/frame.py` and `runtime/ledger.py` are substantially stronger than legacy and should be treated as style anchors.

## Severity-Ranked Findings

### P0 (Correctness)

#### F-P0-001: PLANNING result contract in `ResolutionPhase` docstring is now wrong for vm38
- File/line: `engine/src/tangl/vm38/resolution_phase.py:33`
- Drift type: wrong behavior contract
- Current contract (docs): says PLANNING typically composes to `PlanningReceipt`.
- Actual behavior: vm38 PLANNING (`do_provision`) is side-effect-only and **rejects non-`None` handler returns** with `TypeError`.
- Evidence:
  - `engine/src/tangl/vm38/dispatch.py:162`
  - `engine/tests/vm38/test_dispatch.py:192`
- Intended contract: PLANNING mutates/provisions in place; no aggregated planning receipt is returned by vm38 phase bus.
- Legacy inspiration: `engine/src/tangl/vm/provision/resolver.py` separates planning summary objects from phase-bus aggregation mechanics.
- Status: fixed in this pass.

#### F-P0-002: Affordance linkage contract is inconsistent with declared frontier invariant
- File/line: `engine/src/tangl/vm38/provision/requirement.py:188`, `engine/src/tangl/vm38/provision/requirement.py:209`, `engine/src/tangl/vm38/provision/resolver.py:144`
- Drift type: contract inconsistency (intent vs implementation/tests)
- Canonical contract (maintainer-confirmed): frontier is always `predecessor`; dependency fills missing `successor`; affordance is push-style and should provide resource via `successor`.
- Current behavior (before fix):
  - Class prose stated the canonical contract.
  - `Affordance.set_provider()` synchronized provider to `predecessor` (not `successor`).
  - vm38 tests asserted predecessor-sync behavior.
- Fixed behavior:
  - `Affordance.set_provider()` now synchronizes provider to `successor`.
  - `Resolver._iter_local_affordance_providers()` now scans outgoing affordances from frontier and reads providers from `successor`.
  - vm38 requirement/resolver tests were updated to enforce this contract.
- Evidence:
  - `engine/src/tangl/vm38/provision/requirement.py:209`
  - `engine/src/tangl/vm38/provision/resolver.py:154`
  - `engine/tests/vm38/test_requirement.py:167`
  - `engine/tests/vm38/test_resolver.py:234`
- Intended contract: keep frontier=`predecessor` invariant and align affordance provider linkage and dependent docs/tests to push via `successor`; affordances resolve first and cheaply satisfy dependencies when the affordance `successor` matches dependency requirements.
- Legacy inspiration: directional clarity from `engine/src/tangl/vm/provision/requirement.py` constraint model and offer arbitration flow.
- Status: fixed in this pass.

### P1 (Semantic Ambiguity / Stale Contracts)

#### F-P1-001: `ResolutionPhase` cross-references still point to legacy namespaces
- File/line: `engine/src/tangl/vm38/resolution_phase.py:22`, `engine/src/tangl/vm38/resolution_phase.py:34`, `engine/src/tangl/vm38/resolution_phase.py:35`, `engine/src/tangl/vm38/resolution_phase.py:36`
- Drift type: stale name/path
- Current contract: references `tangl.core.dispatch.call_receipt`, `tangl.vm.planning.PlanningReceipt`, `tangl.core.BaseFragment`, and `tangl.vm.replay.Patch`.
- Intended contract: references should use vm38/core38 symbols and current return shapes.
- Legacy inspiration: `engine/src/tangl/vm/__init__.py` conceptual map with explicit curated symbols.
- Status: fixed in this pass.

#### F-P1-002: `do_gather_ns` docs contradict actual ancestor walk direction
- File/line: `engine/src/tangl/vm38/dispatch.py:231` vs `engine/src/tangl/vm38/dispatch.py:264`
- Drift type: semantic contradiction
- Current contract: prose says walk ancestor chain "from root to node".
- Actual behavior: iterates `node.ancestors` in native order `[node, parent, ..., root]`, then builds `ChainMap(*layers)` so closest scope wins.
- Intended contract: explicitly document node-to-root walk and closest-scope precedence.
- Legacy inspiration: scoped namespace semantics in `engine/src/tangl/vm/context.py` (`ChainMap` layering and cache semantics).
- Status: fixed in this pass.

#### F-P1-003: vm38 package-level conceptual map regressed vs legacy vm
- File/line: `engine/src/tangl/vm38/__init__.py:1`
- Drift type: missing architecture-level API explanation
- Current contract: export list with inline comments only.
- Intended contract: package docstring with `Conceptual layers` and `Design intent` per docstring guide.
- Legacy inspiration: `engine/src/tangl/vm/__init__.py`.
- Status: fixed in this pass.

### P2 (Coverage / Style)

#### F-P2-001: Provisioning docs regressed significantly in refactor target modules
- Files:
  - `engine/src/tangl/vm38/provision/provisioner.py`
  - `engine/src/tangl/vm38/provision/requirement.py`
  - `engine/src/tangl/vm38/provision/resolver.py`
- Drift type: missing API explanation
- Observation: these modules are now the primary vm38 planning surface but have sparse or zero callable-level docs.
- Legacy inspiration:
  - `engine/src/tangl/vm/provision/provisioner.py`
  - `engine/src/tangl/vm/provision/requirement.py`
  - `engine/src/tangl/vm/provision/resolver.py`

#### F-P2-002: Replay docs are under-specified where contracts matter most
- Files:
  - `engine/src/tangl/vm38/replay/patch.py`
  - `engine/src/tangl/vm38/replay/engine.py`
  - `engine/src/tangl/vm38/replay/observer.py`
- Drift type: missing invariant/API explanation
- Observation: replay record invariants (hash guards, operation semantics, checkpoint guarantees) are mostly implicit in code/tests.
- Legacy inspiration: `engine/src/tangl/vm/replay/patch.py` class-level `Why / Key Features / API` structure.

#### F-P2-003: Subpackage `__init__` conceptual docs missing in nested vm38 packages
- Files:
  - `engine/src/tangl/vm38/provision/__init__.py`
  - `engine/src/tangl/vm38/replay/__init__.py`
  - `engine/src/tangl/vm38/runtime/__init__.py`
- Drift type: style-guide divergence
- Guide reference: `docs/src/contrib/docstring_style.md` section "Subpackage `__init__.py` docstring".

### P3 (Polish)

#### F-P3-001: Header underline style drift (`Why` uses mixed underline lengths)
- Example files:
  - `engine/src/tangl/vm38/runtime/frame.py:108`
  - `engine/src/tangl/vm38/runtime/frame.py:327`
- Drift type: style consistency
- Intended: align with `docs/src/contrib/docstring_style.md` header conventions for predictable Sphinx output and diff stability.

## Rewrite Snippet Pack (P0/P1)

### S-P0-001 (`resolution_phase.py` class docstring contract fix)
```python
class ResolutionPhase(IntEnum):
    """
    Phases in a single resolution step.

    Why
    ----
    Defines the ordered pipeline for one frame and the vm38 phase-bus
    aggregation contracts used by :mod:`tangl.vm38.dispatch`.

    Key Features
    ------------
    * **Order** – ``INIT → VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS``.
    * **Explicit reduction** – each phase has a concrete aggregated result shape.

    Notes
    -----
    * ``PLANNING`` in vm38 is side-effect-only provisioning; handlers must return
      ``None`` (non-``None`` raises ``TypeError`` in ``do_provision``).
    * ``JOURNAL`` returns ``Record | Iterable[Record] | None``.
    * ``FINALIZE`` returns ``Record | None``.
    """
```

### S-P1-001 (`resolution_phase.py` stale cross-reference cleanup)
```text
Defines the ordered pipeline for one frame and the vm38 phase-bus
aggregation contracts used by :mod:`tangl.vm38.dispatch`.
```

```text
* ``JOURNAL`` returns ``Record | Iterable[Record] | None``.
* ``FINALIZE`` returns ``Record | None``.
```

### S-P1-002 (`dispatch.py` ancestor-order wording fix)
```python
def do_gather_ns(node: Node, *, ctx) -> ChainMap[str, Any]:
    """Build a scoped namespace by walking the ancestor chain.

    Walks ``node.ancestors`` (which includes ``node`` itself) from node to
    root. At each ancestor, fires all ``gather_ns`` handlers with
    ``caller=ancestor``. Results are merged into a :class:`ChainMap` where
    closer scope (node) overrides more distant scope (root).
    """
```

### S-P0-002 (`provision/requirement.py` affordance/dependency directional contract)
```python
class Affordance(Edge, HasRequirement[PT], Generic[PT]):
    """
    Push-style resource edge carrying a :class:`Requirement`.

    Contract
    --------
    Frontier is always ``predecessor``. The pushed resource/provider is the
    ``successor`` that satisfies the requirement.

    Dependencies and affordances share the same frontier anchor
    (``predecessor``), but opposite resource flow semantics:
    - Dependency: frontier pulls by filling missing ``successor``.
    - Affordance: frontier receives pushed resource at ``successor``.
    """
```

### S-P1-003 (`vm38/__init__.py` conceptual map)
```python
"""
.. currentmodule:: tangl.vm38

Virtual machine mechanisms for phase-driven traversal, provisioning, and replay.

Conceptual layers
-----------------

1. Resolution runtime

   - :class:`Frame` executes one choice resolution loop.
   - :class:`Ledger` persists cursor, stack, and replay artifacts across choices.
   - :class:`ResolutionPhase` defines causal phase ordering.

2. Traversal contracts

   - :class:`TraversableNode` / :class:`TraversableEdge` define cursor movement.
   - :mod:`tangl.vm38.traversal` provides pure history/call-stack queries.

3. Provisioning

   - :class:`Requirement`, :class:`Dependency`, :class:`Affordance` define frontier constraints.
   - :class:`Resolver` and provisioners satisfy constraints from entity/template scopes.

4. Replay artifacts

   - :class:`Event`, :class:`Patch`, :class:`StepRecord`, :class:`CheckpointRecord`
     provide deterministic replay and rollback primitives.

Design intent
-------------
`vm38` defines deterministic execution mechanics and contracts while remaining
policy-agnostic about story/domain semantics, which belong in higher layers.
"""
```

## Optional P2 Snippet Set (Prioritized)
1. `engine/src/tangl/vm38/provision/resolver.py`:
   - Add module docstring with `Why / Key Features / API` and concise docs for `ResolverCtx`, `Resolver.from_ctx`, `gather_offers`, and `resolve_dependency`.
2. `engine/src/tangl/vm38/provision/provisioner.py`:
   - Add module/class docs for `ProvisionPolicy`, `ProvisionOffer`, `Provisioner` protocol, and concrete provisioners.
3. `engine/src/tangl/vm38/replay/patch.py`:
   - Add `Patch`/`Event` invariant docs (pre/post hash checks, allowed operation payload shapes).
4. `engine/src/tangl/vm38/provision/requirement.py`:
   - Add class-level `Why / Key Features / API` for `Requirement` and `HasRequirement`, and method-level docs that enforce frontier=`predecessor`, affordance provider=`successor`.
5. Subpackage docs:
   - Add conceptual-map docstrings to `runtime/__init__.py`, `provision/__init__.py`, `replay/__init__.py`.

## Reusable Rubric for story38/service38 (after vm38)
1. Contract truthfulness: docs must match tested return shapes and failure modes.
2. Refactor fidelity: no stale `tangl.vm`/`tangl.core` namespace references.
3. Phase/ordering fidelity: prose ordering must match actual execution and aggregation.
4. Scope semantics clarity: ancestor traversal direction and override precedence explicit.
5. Constraint semantics clarity: requirement/provider linkage invariants explicit.
6. Artifact invariants explicit: replay/hash/checkpoint assumptions documented.
7. Package map quality: each subpackage `__init__` includes conceptual layers + design intent.
8. Public callable coverage: non-trivial public callables carry concise contract docstrings.
9. Style compliance: section header conventions and terminology align with `docstring_style.md`.
10. Truth gate: doctests and package tests stay green after doc updates.
