# Coding Style & Architecture (semantic)

> Reference implementation priorities: **correctness**, **clarity**, **composability**.
> Lower layers stay **generic & abstract**; domain/presentation live above clean interfaces.

## 0) North star
- Small, explicit mechanisms over clever magic.
- Deterministic and auditable: same inputs → same outputs; mutations become artifacts.

## 1) Layering & dependencies

```
core   (entities, registries, graph topology, records, dispatch, capability)
  ↑
vm     (phases, frame/context, planning, provisioning, events & replay, ledger)
  ↑
service (domains/adapters, IO ports, orchestration, media/presentation hints)
  ↑
app    (CLI, notebooks, integrations, demo scenarios)
  ↑
presentation (renderers, web/UI)
```

**Rules**
- One-way arrows; no imports up the stack.
- Lower layers define **data shapes + contracts**; upper layers implement **policies**.
- Cross-layer communication via **handlers** and **records**—not hidden globals.

## 2) Packages & modules
- **Package** for a new conceptual layer (`core`, `vm`, `service`).
- **Module** for cohesive micro-domains (`replay/event.py`, `planning/offer.py`).
- **Single-class module** is fine; keep module docstring to 1–3 lines or omit.

## 3) Class design
- **Nouns are small**: data-first + a few sharp methods.
- **Records are immutable**: `Event`, `Patch`, `Snapshot`, `Fragment`.
- **Hooks over overrides** where it improves clarity—use `_structure_post/_unstructure_post` to avoid mutual recursion.  
  *Alternate pattern allowed:* explicit `structure/unstructure` overrides with a clear base case and round-trip tests.

## 4) Data model & serialization
- Pydantic v2 models for entities and records.
- `Entity.structure(data)` is the factory; `unstructure()` emits a minimal, portable dict (class tag + uid).
- No implicit IO in models; persistence belongs to ledger/service.

## 5) Mutations & replay
- Plan → Project → Commit. Planning computes intent; commit applies and logs artifacts.
- Prefer event sourcing: snapshot + canonicalized patches.
- Receipts are the audit trail of runtime decisions.

## 6) Handlers & dispatch
- Handlers are entity-centric; dispatch orders by priority → registration → uid.
- Selection via `Selectable`/criteria; avoid hard-coded switches.
- Thin handler bodies, rich `JobReceipt`s for aggregation and audit.

## 7) Naming & API surface
- Canon: `Graph`, `Node`, `Edge`, `Subgraph`; `Record`, `Event`, `Patch`, `Snapshot`, `Fragment`; `Frame`, `Context`, `Ledger`; `Requirement`, `Offer`, `Provisioner`.
- Enum members UPPERCASE; phases are UPPERCASE.
- Curate public surface with `__all__`.

## 8) Extensibility & hooks
- Registries as extension points; publish `selection_criteria`.
- Template-driven provisioning; no hard-coded class awareness.
- Presentation hints are advisory; clients may ignore.

## 9) Errors & invariants
- Fail fast at boundaries (arity/role checks; policy validation).
- Exceptions include context (ids, labels, policy).
- No silent coercion.

## 10) Determinism & RNG
- `Context.rand` is seeded from `(graph.uid, cursor.uid, step)`.
- No time-based randomness in `core`/`vm`.

## 11) Performance posture
- Optimize query paths; accept small constants for clarity elsewhere.
- Canonicalization linear-ish; avoid n² passes.

## 12) Observability
- Prefer emitting a `Record` to logging when it affects reasoning.
- Minimal structured logs at orchestration edges.

## 13) Tests (contracts > mechanics)
- Round-trip `structure/unstructure` for composites.
- Phase reducers return the documented shape.
- Provisioning policies enforce required fields.
- Event canonicalization removes redundant updates; replay reproduces state.
- Deterministic RNG in tests; monkeypatch randomness when needed.

## 14) Anti-patterns
- Upward imports (lower layer depending on higher).
- Hidden globals/state; domain singletons leaking into `core`/`vm`.
- Recursive factories without a base case.
- Overgrown classes; mix responsibilities → extract helpers.
- Implicit IO in `core`/`vm`.
