# StoryTangl Contributor Guide

Welcome! This project powers StoryTangl, an abstract narrative graph engine.
Use this file as the quick-reference guide for design philosophy, coding
conventions, and the core ideas you should understand before contributing.

**Read `ARCHITECTURE.md` first.** It describes what the system *is* — the
concepts, types, and invariants. This file describes how to *work in* it.

This is a **research platform and reference implementation**, not a production
SaaS product. Code clarity, conceptual integrity, and ease of comprehension
are more important than robustness against hypothetical misuse.


## Design philosophy

These principles override all other guidance in this document. When in doubt,
choose the option that leaves the code easier to read in five minutes.

### 1. Parsimony

A proof with 4 statements is better than a proof with 100 statements that
reduce to the same argument. One takes 4% of the cognitive load of the
other. The same applies to code.

- **The shortest correct solution is the best solution.** If you can do it
  in 10 lines, do not do it in 40. If you can do it with one type, do not
  create three. If you can do it with a direct call, do not add a layer of
  indirection.
- **Economy is a design quality, not a shortcut.** Fewer moving parts means
  fewer places for bugs to hide, fewer things to hold in your head, fewer
  joints that can fail.
- **If the design is right, change the test.** Tests are consequences of
  design, not constraints on it. Do not contort an implementation to pass
  a test that encodes a wrong assumption. Fix the test.

### 2. Trust the types

StoryTangl has well-defined types at every layer. Use them.

- **Do not `getattr` your way around typed interfaces.** If a function
  receives a `PhaseCtx`, access `.graph` directly — do not write
  `getattr(ctx, "graph", None)`. If the type is wrong, let it fail loudly.
- **Do not accept `Any` when a concrete type is known.** `_ctx: Any` as a
  parameter type is a design smell. Use the protocol (`VmPhaseCtx`,
  `VmResolverCtx`) or the concrete class (`PhaseCtx`). If multiple context
  types are possible, use a `Union` or a shared protocol.
- **Do not add `isinstance` guards for types the caller is already required
  to provide.**
- **Use protocols for duck typing, not runtime probing.** Do not scatter
  `hasattr`/`getattr`/`callable(getattr(...))` probes through code.

The only valid exception is interop boundaries where data arrives from
persistence, user input, or external systems with genuinely unknown shape.

### 3. Minimize cognitive overhead

Every line of code has a reading cost. Minimize total cost.

- **Prefer direct expression over indirection.** A 3-line function body is
  better than a 1-line call to a helper that exists nowhere else.
  Conversely, if you see the same 3-line stanza pasted in 5 places, extract
  it once and name it well.
- **Do not add layers "for flexibility."** No abstract base class with one
  concrete subclass. No strategy pattern with one strategy. No registry
  when a dict suffices. No factory when a constructor suffices.
  Add the abstraction *when the second use case arrives*, not before.
- **Do not write code to handle cases that cannot arise.** If the graph
  always has a cursor during phase execution, do not write `if cursor is None:
  return`. If a function is only called from one site and that site always
  passes a non-None value, do not guard against None.
- **Do not add compatibility shims preemptively.** If a rename happens,
  update the callers. A shim is warranted only when external consumers
  exist that you cannot update (e.g., persisted pickle references).

### 4. Reuse existing patterns

The codebase already has well-tested mechanisms. Use them before inventing
alternatives. **See `ARCHITECTURE.md` for the canonical type map.**

- **Selector** is how you query entities. Do not write bespoke filter loops.
- **BehaviorRegistry** and `chain_execute_all` is how you compose dispatch.
  Do not invent new plugin/hook registries.
- **`PhaseCtx.derive()`** is how you create a child context for a different
  cursor. Do not manually pluck fields off a context to build another one.
- **EntityTemplate → materialize** is how you create runtime entities from
  authored data. Do not bypass this with direct constructor calls unless the
  entity is genuinely ephemeral (like an `AnonymousEdge`).
- **`_DESIGN.md` files** in each subpackage describe the intended shape.
  Read the relevant design doc before adding a new module or public class.
  If your addition doesn't fit the described shape, discuss the mismatch
  before proceeding.

### 5. Keep layer boundaries sharp

```
Service  → Lifecycle, persistence, transport, access control
Story    → Narrative vocabulary, compilation, materialization, journal content
VM       → Phase pipeline, provisioning, traversal mechanics, replay
Core     → Timeless primitives: entity, registry, graph, selector, dispatch
```

- Import only downward. Story may import VM and Core. VM may import Core.
  Service may import all three. **Never import upward.**
- If a function needs knowledge from a higher layer, accept it as a callback
  or protocol parameter — do not import the module.
- If you find yourself wanting to import `tangl.story` from `tangl.vm`, the
  feature belongs in story, not vm. Move it.

### 6. Prefer deletion over annotation

If code is not used, delete it. Do not comment it out. Do not add a
`# deprecated` or `# legacy` marker and leave it. `git` remembers.

- **No `# TODO: maybe...` on speculative features.** File an issue or delete
  the comment.
- **No legacy compatibility shims without a documented consumer.** If you
  cannot name the call site that needs the shim, the shim is dead code.
- **No accumulation of "just in case" parameters.** If a parameter is always
  passed as `None` or `False`, remove it.

### 7. Stop and escalate, don't work around

**If you find yourself doing any of the following, STOP and surface the
design question instead of solving it locally:**

- Creating a parallel version of a type that already exists elsewhere.
- Writing a custom serializer or validator for something that is (or should
  be) a Singleton. Singletons already serialize as `(class, label)`.
- Writing more than 3 lines of type coercion or defensive probing.
- Adding a bridge, adapter, or shim between two things that should be the
  same thing.
- Adding a parameter, field, or flag to handle a case that only arises
  because of a decision made upstream.
- Catching a broad exception to suppress a type error, import error, or
  attribute error that "shouldn't happen."

The right response to friction is to ask whether the upstream decision is
wrong, not to absorb the friction into more code.

---

## Design invariants

These are structural facts about the system. If you find yourself violating
one, it means either the code you're looking at is wrong, or the thing
you're trying to do belongs somewhere else. **See `ARCHITECTURE.md` for the
full type map and rationale.**

- **One fragment hierarchy.** `BaseFragment` (core) is the base.
  `journal/fragments.py` defines the concrete reusable fragment types.
  Compatibility re-exports may exist, but there is no second fragment model.
- **One context type for phase execution.** `PhaseCtx` is the concrete
  runtime context for the phase pipeline. Use it directly or call
  `.derive()` for a child context. Do not create alternative context types.
- **Singletons serialize themselves.** `Singleton.unstructure()` produces
  `{"kind": Class, "label": "x"}`. `Singleton.structure(data)` looks up the
  live instance. Do not write custom serializers, validators, or reference-
  tracking machinery for Singletons.
- **One dispatch mechanism.** `BehaviorRegistry.chain_execute_all` is how
  behaviors compose. `on_*/do_*` hooks in `core.dispatch`, `vm.dispatch`,
  and `story.dispatch` are the registration surfaces. Do not create
  alternative hook systems.
- **One authority-chain mechanism.** Core `Graph` delegates
  `get_authorities()` to `self.factory` when a singleton graph authority is
  bound. Story still has a transitional `StoryGraph` override that layers
  story and world authorities on top, but new features should move toward
  the same factory-bound authority model rather than inventing parallel
  registries or discovery seams.
- **One template → entity path.** `EntityTemplate.materialize()` is the core
  shape-instantiation path. Higher layers may add policy or post-
  materialization behavior, but they should not bypass the template system.
- **Import direction is a strict DAG.** `core ← vm ← story ← service`.
  No cycles, no upward imports, no conditional cross-layer imports.
- **Every entity in the runtime graph is an Entity subclass.** If something
  lives in the graph, it inherits from `Entity` or a graph-aware descendant
  such as `Node`, `Edge`, or `Record`.
- **The journal is the only narrative output surface.** JOURNAL phase
  handlers produce fragments. Service delivers fragments. There is no
  parallel content channel.

---

## Repository layout
- `engine/src/tangl/`: primary Python package with the runtime engine.
- `engine/tests/`: canonical test suite (pytest based).
- `apps/` and `worlds/`: optional entry points and sample content.
- `docs/`: Sphinx documentation sources.

## Orientation bundles
- If the runtime has `repomix` installed, you may use curated opt-in bundles for broad repo orientation or cross-cutting work instead of scanning the whole repo ad hoc.
- Generate them with `python3 scripts/repomix_bundle.py --list` and then request only the smallest relevant bundle such as `foundation`, `service-persistence`, `mechanics-media-prose`, `apps`, or `docs-index`.
- Generated outputs live under `tmp/repomix/`. You may consult pre-generated bundles there when present, but regenerate them if the task touches changed areas or the bundle appears stale.
- Treat bundles as orientation aids, not source of truth. Read and edit the real repository files before making code changes.

## Coding style
- Target **Python 3.13**. Use `from __future__ import annotations` for forward
  references.
- **Type hints everywhere.** Prefer concrete types (`list[str]`, not
  `Iterable[Any]`). Reuse aliases from `tangl.type_hints`.
- Engine models inherit from **`BaseModelPlus`** or other Pydantic models.
  Use it for new persistent entities unless you have a strong reason not to.
- Explicit, grouped imports: stdlib → third-party → local. No wildcards.
- Black-like formatting: 4-space indents, trailing commas for diffs, double
  quotes. Lines under 100 characters.
- Module-level loggers: `logging.getLogger(__name__)`. Structured messages,
  no f-strings inside log calls.
- See `docs/src/contrib/coding_style.md` for deeper rationale.

## Docstrings and comments
- **reStructuredText** for Sphinx compatibility.
- Follow `Why / Key Features / API / Notes / See also` for public classes
  (see `docs/src/contrib/docstring_style.md`).
- Triple double quotes. Commentary inside docstrings; inline comments only
  for implementation clarification.
- Do not write docstrings that merely restate the function signature. If the
  name and types are self-explanatory, a one-line summary suffices.

## Testing
- Run `pytest engine/tests` before submitting changes.
- Use the poetry-managed venv. Add test paths to `PYTHONPATH` if needed.
- Keep fixtures lightweight and deterministic.
- See `engine/tests/AGENTS.md` for detailed test conventions.

## Configuration
- Dynaconf via `tangl.config.settings` and `defaults.toml`.
- Paths under `[service.paths]` with `@path` casting.
- Read config through `tangl.config.settings` or its helpers.
- Do not introduce parallel settings systems.

### Media & Binary Assets (PNG / LFS safety)

StoryTangl uses Git LFS for `.png` and `.jpg` files.

1. **Never create PNG/JPG files inside the repository.**
2. **Use SVG primitives** for examples and test worlds.
3. **Create SVG files only in `tmp_path`** during tests, not in the repo.

## Miscellaneous
- No try/except around imports. Declare dependencies in `pyproject.toml`.
- `Path` objects over raw strings for filesystem paths.
- Use `model_dump`/`model_validate`, not manual dict munging.
- If updating an implementation detailed in a `_DESIGN.md` doc, update the
  doc's status section so it does not go stale.
