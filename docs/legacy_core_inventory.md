# Legacy Core Feature Inventory

## Purpose

This note surveys the historical `scratch/legacy/core` iterations alongside the modern
`tangl.core` package. It highlights reusable mechanics that shaped the handler pipeline,
context assembly, and graph orchestration so we can recover proven ideas when extending
the current `core` + `vm` runtime.

## Core/VM architecture map (ported from `notes_v34`)

```mermaid
flowchart LR
    subgraph tangl.core
        subgraph Entities
            Entity
            Registry -- manages --> Entity
        end
        subgraph Graph
            Graph -- extends --> Registry
            Node -- extends --> Entity
            Edge -- extends --> Entity
            Graph -- owns --> Node
            Graph -- owns --> Edge
        end
        subgraph Domain
            Domain -- extends --> Entity
            StructuralDomain -- extends --> Domain
            AffiliateDomain -- extends --> Domain
            Scope -- layers --> Domain
            Scope -- aggregates --> Handler
        end
        subgraph Dispatch
            Handler -- extends --> Entity
            DispatchRegistry -- extends --> Registry
            DispatchRegistry -- yields --> Handler
            JobReceipt -- extends --> Entity
            Handler -- produces --> JobReceipt
        end
        subgraph Records
            Record -- extends --> Entity
            StreamRegistry -- extends --> Registry
            StreamRegistry -- stores --> Record
        end
        subgraph Fragments
            BaseFragment -- extends --> Entity
        end
    end

    subgraph tangl.vm
        ResolutionPhase --> Frame
        Frame -- builds --> Context
        Context -- caches --> Scope
        Context -- iterates --> Handler
        PlanningReceipt -- aggregates --> JobReceipt
    end

    Frame -- writes --> StreamRegistry
    Frame -- consults --> DispatchRegistry
    AffiliateDomain -- registers --> DispatchRegistry
    Scope -- queries --> DispatchRegistry
```

The diagram updates the `notes_v34` system map to the current packages: entities sit at the core, graphs reuse registries, domains stack into scopes, and the VM’s frame/context pair invokes handlers across the phase bus while journaling to record streams.【F:scratch/overviews/notes_v34.md†L5-L97】【F:engine/src/tangl/core/entity.py†L24-L147】【F:engine/src/tangl/core/graph/node.py†L11-L62】【F:engine/src/tangl/core/domain/domain.py†L14-L47】【F:engine/src/tangl/core/domain/affiliate.py†L1-L41】【F:engine/src/tangl/core/domain/scope.py†L1-L104】【F:engine/src/tangl/core/dispatch/dispatch_registry.py†L1-L84】【F:engine/src/tangl/core/record.py†L31-L168】【F:engine/src/tangl/vm/frame.py†L1-L200】【F:engine/src/tangl/vm/context.py†L1-L114】【F:engine/src/tangl/vm/planning/__init__.py†L1-L15】

## How handler dispatch evolved

### Strategy handlers (core-21)
- `core-21` introduced a task-centric plugin system that merged MRO lookups, domain
  decorators, and priority-based execution modes (first/all/merge/iter).【F:scratch/legacy/core/core-21/task_handler-2/__init__.py†L1-L34】
- Early service wrappers already documented the expectation that a task call discovers
  inherited and domain-supplied hooks, then aggregates results via configurable
  strategies.【F:scratch/legacy/core/core-21/task_handler-2/__init__.py†L18-L34】

### HandlerPipeline and registries (core-32 → core-34)
- `core-32`/`core-34` refactored handlers into explicit registries (`HandlerPipeline`,
  later `HandlerRegistry`) with deterministic ordering, aggregation strategies, and
  support for injecting extra handlers at call time.【F:scratch/legacy/core/core-34/dispatch/handler_registry.py†L58-L195】
- Pipelines were assigned to specific lifecycle concerns:
  - **Context gathering** merged per-entity locals, `self`, and derived flags via the
    shared `on_gather_context` registry.【F:scratch/legacy/core/core-34/services/context.py†L13-L50】
  - **Rendering** wrapped Jinja templates so narrative blocks could render against the
    gathered namespace before journaling.【F:scratch/legacy/core/core-34/services/rendering.py†L23-L115】
  - **Predicates & effects** normalized runtime `eval`/`exec` expressions behind
    sandboxed helpers that re-used `safe_builtins`.【F:scratch/legacy/core/core-34/services/runtime_object.py†L14-L57】
- Association hooks fired whenever nodes linked or unlinked, giving mixins a single
  place to enforce bidirectional bookkeeping or propagate derived edges.【F:scratch/legacy/core/core-32/graph_handlers/associating.py†L10-L161】

### Portable IR focus (core-36)
- `core-36` slimmed entities down to DTO-friendly records with explicit FQN serialization
  and kept author data in `Node.locals` so scopes could rebuild namespaces during replay.
  Effects were expected to mutate state via event sourcing rather than direct methods.【F:scratch/legacy/core/core-36/entity.py†L5-L136】

## Legacy graph assumptions to remember

- Structural containment was a tree: each node tracked a single `parent_id` and a list of
  child ids; adding a child reassigned parents to preserve a DAG-like hierarchy.【F:scratch/legacy/core/core-32/graph/node.py†L100-L199】
- Traversal logic assumed choice edges lived under structural parents and were grouped by
  redirect/continue/block triggers, sequencing availability checks, effect execution, and
  content generation in one enter routine.【F:scratch/legacy/core/core-32/graph_handlers/traversable.py†L11-L134】
- Association handlers filled the gap for non-tree relationships (roles, peer links) by
  mirroring links on both participants and enforcing reciprocity when nodes were
  connected or disconnected.【F:scratch/legacy/core/core-32/graph_handlers/associating.py†L38-L161】
- Phase notes from `core-33` already separated gather → resolve → gate → render → finalize,
  foreshadowing the modern VM phase bus.【F:scratch/legacy/core/core-33/notes.md†L1-L18】

## Mapping to the modern architecture

- `DispatchRegistry` in `tangl.core.dispatch` is the modern successor to the legacy handler
  pipelines: it keeps deterministic ordering, decorator registration, and batch execution
  that now emit `JobReceipt` objects for auditing.【F:engine/src/tangl/core/dispatch/dispatch_registry.py†L1-L82】
- `tangl.vm.Frame` formalizes the phase ladder (VALIDATE → PLANNING → … → FINALIZE) and
  applies the correct reducer for each, letting domains plug handlers into granular
  phases instead of monolithic enter routines.【F:engine/src/tangl/vm/frame.py†L23-L200】
- `tangl.vm.Context` centralizes namespace assembly, scope inference, deterministic RNG,
  and handler lookup—capabilities the old `HasContext`/graph mixins provided ad-hoc.【F:engine/src/tangl/vm/context.py†L1-L114】
- Modern `tangl.core.entity.Entity` preserves the portable-ID mindset while expanding the
  identifier/matching helpers, giving us a compatible foundation for reviving registry-
  driven behaviors.【F:engine/src/tangl/core/entity.py†L1-L115】

## Protocol-driven surfaces worth preserving

- The protocol specs captured expectations for singleton worlds, story factories, traversal nodes, and handler slots, spelling out serialization hooks and cascading namespaces for every object.【F:scratch/protocols/protocols-26.py†L23-L200】 Those same responsibilities now land on `Domain`/`Scope` stacks and VM context helpers instead of bespoke mixins.【F:engine/src/tangl/core/domain/scope.py†L1-L104】【F:engine/src/tangl/vm/context.py†L1-L114】
- Traversable mixins combined predicate tests, effect execution, and rendering in one method; porting them requires registering separate handlers for VM phases so audit receipts stay granular.【F:scratch/protocols/protocols-26.py†L117-L160】【F:engine/src/tangl/vm/frame.py†L23-L140】
- Protocol emphasis on templated instantiation and streamable responses aligns with `StreamRegistry` journaling and `DispatchRegistry` pipeline receipts, helping reintroduce service APIs without rebuilding the monolith.【F:scratch/protocols/protocols-26.py†L10-L200】【F:engine/src/tangl/core/record.py†L31-L168】【F:engine/src/tangl/core/dispatch/dispatch_registry.py†L1-L84】

## Gaps worth resurrecting

1. **Templated rendering & journaling hooks** – Port the Jinja-enabled rendering pipeline
   into a journaling domain that runs during `ResolutionPhase.JOURNAL`, reusing
   `DispatchRegistry` receipts so fragments stay auditable.【F:scratch/legacy/core/core-34/services/rendering.py†L23-L115】【F:engine/src/tangl/vm/frame.py†L23-L200】
2. **Predicate / effect evaluation** – Reintroduce sandboxed `eval`/`exec` helpers as
   planning/update domains. Results can be wrapped in `JobReceipt` data so VM phases keep
   a trail of expressions that were run.【F:scratch/legacy/core/core-34/services/runtime_object.py†L14-L57】【F:engine/src/tangl/vm/frame.py†L48-L68】
3. **Association callbacks** – Define a scope-aware domain that listens for graph link
   mutations (perhaps via patch/watch events) and exposes `on_associate`/`on_disassociate`
   handlers, preserving the reciprocity guarantees authors relied on.【F:scratch/legacy/core/core-32/graph_handlers/associating.py†L38-L161】【F:engine/src/tangl/vm/frame.py†L128-L199】
4. **Tree-first structural helpers** – Provide utilities or mixins that maintain the
   single-parent structural tree while letting dependency edges remain free-form, so we
   can continue to assemble scopes deterministically like the legacy `ancestors`
   calculations did.【F:scratch/legacy/core/core-32/graph/node.py†L136-L199】【F:engine/src/tangl/vm/context.py†L86-L114】
5. **Phase receipts as diagnostics** – The legacy service receipts logged aggregator mode
   and handler ordering; we can revive that ergonomics by enriching `JobReceipt`
   payloads or adding optional debug fragments during FINALIZE for easier spelunking when
   revisiting older behaviors.【F:scratch/legacy/core/core-34/dispatch/handler_registry.py†L18-L195】【F:engine/src/tangl/core/dispatch/dispatch_registry.py†L17-L82】

Capturing these patterns gives us a roadmap for rebuilding missing behaviors on top of the
current phase bus without regressing to the monolithic handler stacks of earlier versions.
