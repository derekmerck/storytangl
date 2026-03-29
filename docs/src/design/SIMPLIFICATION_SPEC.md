# Simplification Spec

**Status:** ACTIVE ARCHITECTURE NOTE  
**Use:** conceptual porting lens and simplification aid for contributors  
**Authority:** explanatory reference only; package design docs and code remain the live contract

---

## Why This Exists

If you had to reimplement StoryTangl in another language, or simplify it
aggressively without changing what it fundamentally is, what concepts would you
actually need to preserve?

This note answers that question at the architectural level. It tries to
separate:

- the engine's essential concepts
- implementation conveniences that exist because this is a Python/Pydantic codebase
- compatibility or migration surfaces that should not be mistaken for design

It is not a rewrite spec and it is not a mandate to collapse the current code
into a tiny core overnight. It is a review lens for deciding what must remain
true when simplifying or porting the system.

---

## Core

The essential core concepts are:

- **Entity**: the universal identity-bearing object with UUID, label, and tags
- **Selector**: the query language for matching entities
- **Registry**: indexed ownership of entities with filtered lookup
- **Graph**: topology over nodes, edges, and subgraphs
- **Record**: immutable appendable fact objects
- **Singleton / Token**: type-vs-instance split for reusable vocabularies
- **EntityTemplate**: compile, decompile, and materialize path for authored shapes
- **BehaviorRegistry**: the one composition and dispatch mechanism
- **Namespace contribution**: local publication of symbols without bespoke per-feature wiring

What is usually accidental here:

- Python or Pydantic reflection scaffolding
- legacy alias fields and compatibility helpers
- convenience factories that duplicate direct construction
- defensive probing around already-typed interfaces

If a simplification keeps the above concepts intact, it can change most of the
surrounding machinery freely.

---

## VM

The essential VM concepts are:

- **Resolution phases**: ordered causal pipeline for traversal
- **TraversableNode / TraversableEdge**: availability, effects, and redirect-aware movement
- **Frame**: one live resolution pass over the graph
- **PhaseCtx**: dispatch context for phase execution and namespace assembly
- **Ledger**: persistent runtime state across choices
- **Requirement / Dependency / Affordance**: unresolved authored intent in runtime form
- **Provisioners + Resolver**: offer generation, ranking, and binding
- **Traversal queries**: pure visit-history helpers such as visit counts and round/turn derivation

The simplification target is not "delete the VM." It is "keep the pipeline and
remove avoidable overhead." Typical overhead candidates are:

- duplicated context-projection helpers
- typed surfaces bypassed by `getattr` fog
- diagnostics formatting mixed into core resolver flow
- compatibility aliases for older traversal names

The VM should stay explicit about phase ordering, redirects, and provisioning.
That causal clarity is the point.

---

## Story

The essential story-layer concepts are:

- **World** as the story authority over templates, materialization, and story-owned adjuncts
- **StoryGraph** as the runtime graph carrying world context
- **Episode vocabulary** such as scenes, blocks, menu blocks, and actions
- **Compiler / materializer split** between authored data and runtime entities
- **Journal fragments** as the narrative output surface
- **World-authored hooks** for story-specific policy that should not leak into VM internals

The story layer is where authored semantics live. Simplification should remove
duplication and historical residue, but not flatten story concepts back into raw
graph mechanics.

Good simplifications here usually look like:

- fewer parallel representations of the same authored idea
- clearer entry, compilation, and materialization contracts
- more direct authority seams from world to runtime

Bad simplifications usually look like:

- pushing story knowledge downward into VM
- replacing world-owned policy with transport- or service-owned special cases

---

## Service

The essential service-layer concepts are:

- **ServiceManager** as the explicit public orchestration surface
- **user / ledger session management**
- **typed response envelopes and projections**
- **auth and access control at the transport boundary**
- **resource lookup and mutation through service methods, not ad hoc graph poking**

The service layer exists to mediate lifecycle, persistence, transport, and
access, not to reinterpret story semantics. Simplification here usually means:

- fewer response-model variants where one typed shape will do
- clearer session contracts
- less controller indirection
- direct use of the canonical service method metadata rather than parallel routing logic

---

## What Counts As Accidental Complexity

These are common signs that code is implementation-heavy rather than concept-heavy:

- compatibility aliases that exist only for old names
- abstract layering added before a second real use case exists
- runtime probing where a typed protocol already defines the surface
- helper chains that obscure one direct operation
- response or DTO families that differ cosmetically rather than semantically
- Python-specific metaprogramming that does not change the underlying model

Not all of this should be deleted immediately. But it should all be viewed as
suspect until it proves its value.

---

## How To Use This

### 1. Preserve Concepts, Not Incidental Shapes

When simplifying, ask whether a change preserves:

- identity
- topology
- phase causality
- template-to-entity materialization
- world authority
- journal as the output surface

If yes, the exact helper structure may be negotiable.

### 2. Prefer Direct Typed Paths

If the caller already has a `PhaseCtx`, `World`, or `ServiceManager`, use that
surface directly. Many simplification wins come from deleting probes and
bridges, not from inventing better abstractions.

### 3. Delete Dead Weight Before Generalizing

Compatibility shims, legacy aliases, and duplicate helper paths are often a
better deletion target than the real architecture. Trim those first.

### 4. Use It As A Porting Checklist

A clean port should be able to explain:

- how entities and registries work
- how traversal phases run
- how provisioning resolves authored requirements
- how worlds author story semantics
- how the service layer exposes typed runtime state

If a candidate design cannot explain those clearly, it is probably simplifying
the wrong thing.

---

## Non-Goals

- prescribing exact line counts or class counts
- forcing the current repo to mirror a hypothetical port
- treating every convenience helper as design failure
- replacing subsystem-specific design docs

This document is most useful as a review lens: what must remain true, what can
be simplified, and what should stop being treated as architecture when it is
really just implementation residue.
