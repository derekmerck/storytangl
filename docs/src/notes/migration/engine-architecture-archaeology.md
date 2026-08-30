# Engine Architecture Archaeology

This note preserves the useful design precedent from the retired
``scratch/legacy`` engine snapshots. The implementations themselves were
removed after the v38 cutover because they were neither executable contracts
nor clearer references than the current engine. Git history remains the source
for exact historical code.

## What the experiments established

### Explicit dispatch beat general plugin machinery

The v2 experiments used ``pluggy`` and then increasingly flexible MRO-driven
task pipelines. They demonstrated that a generic plugin manager made handler
priority and overlapping responsibility difficult to see. The durable result is
the current explicit ``BehaviorRegistry`` and phase-hook vocabulary: one
dispatch mechanism, deterministic ordering, and world/domain authorities that
state where behavior comes from.

### Constructor form beat automorphic construction

``Automorphic``, ``Templated``, and ``SmartNew`` explored data-driven
self-casting, inferred subclasses, and default/template lookup during object
creation. These were clever demonstrations of how much Python could infer, but
they hid ownership and made persistence shape difficult to reason about. The
current explicit ``unstructure()`` / ``structure()`` contract and
``EntityTemplate.materialize()`` path retain polymorphic construction without
the inference pipeline.

This is also a negative precedent: embedded constructor-form values opt in;
graph entities normally persist by reference; field names and defaults do not
silently determine object types.

### Context services converged into a phase context

The v3.3-v3.4 capability/service experiments represented context gathering,
predicates, effects, rendering, and provisioning as injectable entity services.
They clarified the operations the engine needs, but made the execution model
more abstract than the work itself. The useful vocabulary survived as typed
phase hooks operating on one ``PhaseCtx`` and composing through the behavior
registry.

### Domains separated scope from engine layers

The v3.7 domain and scope work established two lasting ideas: structural
ancestry contributes local namespace, and a world may contribute policy and
behavior without importing that policy upward into core. Earlier proposals
cached edge projections inside domain variables and refreshed them after
planning/update. The current design instead derives scoped role/setting values
from live graph state, avoiding a second mutable projection and its cache
invalidation lifecycle.

### Determinism and receipts survived; mutation watchers did not

The v3.7 VM made phase order, handler ordering, receipts, replay, and a separate
journal explicit. Its watched-object event stream was useful instrumentation,
but proxying every mutation proved to be the wrong persistence boundary. The
current ledger, constructor-form snapshots, graph diffs, and receipt streams
preserve deterministic/auditable execution without making observable proxy
behavior part of every domain object.

## Reading the history

The v38 parity matrix records which legacy behavioral tests were ported,
adapted, moved, or intentionally retired. Current contracts live in
``ARCHITECTURE.md`` and the nearest ``*_DESIGN.md`` file. For an exact old
implementation, inspect the repository commit before the hygiene removal
rather than restoring a second source tree beside the active engine.
