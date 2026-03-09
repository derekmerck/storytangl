# Mu-Affordances and Microconcepts

**Document Version:** 0.1  
**Status:** DESIGN NOTE - vocabulary and implementation direction only  
**Prior art:** issue `#113`, issue `#141`, `scratch/mechanics/badge/badge.py`,
`engine/src/tangl/discourse/mu_block.py`, `engine/src/tangl/discourse/dialog.py`  
**Relevant layers:** `tangl.core`, `tangl.vm.provision`, `tangl.story.concepts`,
`tangl.story.episode`, `tangl.discourse`

---

## Problem Statement

StoryTangl already has several objects that are clearly meaningful and structured,
but do not want full graph identity:

- dialog sub-blocks that carry speaker/style metadata before rendering
- badge-like grants that should follow an assigned provider while a link exists
- temporary titles, uniforms, avatars, and similar role-linked decorations
- small provider-side annotations created by planning or provisioning

These objects are "less identified than an Entity" but more meaningful than
plain dict payloads.

They need to be:

- authored or generated in a managed way
- passed through behaviors and handlers
- filtered or ordered deterministically
- projected into namespace, render output, or effective affordances
- discarded cleanly when their context no longer applies

This note refers to that family as **microconcepts**, and to the
provider-binding subset as **mu-affordances**.

---

## Core Insight

A microconcept is not a small Entity. It is a **context-bound concept carrier**
with no standalone graph identity.

An Entity has stable identity because it must be registrable, matchable, and
addressable outside the immediate operation that is using it.

A microconcept is different:

- it is meaningful only relative to a caller, source edge, provider, or render pass
- it may have provenance such as `source_id` or `subject_id`
- it does not belong in the graph registry as an independent peer
- it can still carry labels, tags, locals, media hints, and ordering metadata

In other words, it has **context identity**, not **graph identity**.

This is the common thread between:

- `MuBlock` in discourse parsing
- old dynamic badges
- role-linked derived grants from issue `#141`
- future provider overlays created by dependencies, affordances, or fanout

---

## Why "Fragment" Is Not the Right Word

"Fragment" already has a strong meaning in StoryTangl: rendered or journal-ready
output records such as content fragments, dialog fragments, media fragments, and
control fragments.

That meaning is useful and should stay stable.

Microconcepts come **before** fragment output, or may never become fragments at
all. They can be used to:

- enrich a namespace
- decorate a provider view
- attach effective tags or media
- drive dynamic affordance projection
- parse authored content into more structured intermediate units

So:

- **Fragment** should remain "rendered output artifact"
- **Microconcept** should mean "context-bound entity-like concept carrier"
- **MuBlock** is a render-focused microconcept subtype
- **MuAffordance** is a provider-binding microconcept subtype

"Component" is possible vocabulary, but it is already overloaded elsewhere in
engine design. "Microconcept" is the clearer story-facing umbrella.

---

## Existing Prior Art

### 1. MuBlock in discourse parsing

`MuBlock` in `engine/src/tangl/discourse/mu_block.py` already expresses the
basic pattern well:

- smaller than a block
- not persisted in the graph
- carries just enough metadata to behave meaningfully
- promoted into a real output artifact through `to_fragment()`

`DialogMuBlock` in `engine/src/tangl/discourse/dialog.py` shows the same pattern
applied to speaker attribution and dialog styling.

This is the clearest proof that StoryTangl already benefits from managed
non-entity intermediates.

### 2. Dynamic badges

The old badge system in `scratch/mechanics/badge/badge.py` is the "ur
mu-affordance" design.

Its enduring ideas are:

- singleton-authored definitions
- dynamic attach / detach semantics
- topological dependency ordering
- hide / supersede relationships
- projection into both condition context and render output

Its weak point was not the concept. The weak point was the old plumbing:

- explicit mutation of node associations
- global recomputation scans
- tag-like state being pushed into nodes instead of derived from current context

### 3. Role-linked grants

Issue `#141` captures the concrete modern use case:

- a role edge resolves to some provider
- while that edge exists, the provider should gain contextual properties
- when the provider changes, the contextual properties should move with it
- nothing should rely on brittle link / unlink scripts staying in sync

That is exactly what a mu-affordance is:

- declared on a carrier edge
- bound to the currently assigned provider
- projected as derived state
- discarded when the assignment changes

---

## Definition

### Microconcept

A **microconcept** is a serializable or constructible value object that:

- is carried by or derived from a parent entity, edge, template, or render pass
- has no standalone registry identity
- is only meaningful in a specific bound context
- may be promoted into another runtime artifact such as a namespace view,
  effective tag set, affordance decoration, or fragment

### Bound Microconcept

A **bound microconcept** is a runtime binding of a microconcept to a specific
context, such as:

- source node
- carrier edge
- resolved provider
- current caller
- render source id

This is the object that actual handlers consume.

### Mu-Affordance

A **mu-affordance** is a bound microconcept that decorates or exposes a provider
through a relationship.

Examples:

- `boss.title == "boss"` while a role edge is active
- a provider temporarily gains a `uniform` media item through assignment
- a selected provider gains extra tags or labels while filling a task
- a fanout-created affordance carries extra provider-facing menu metadata

### MuBlock

A **MuBlock** is a microconcept that specializes in render-oriented content
structure and usually promotes into fragments.

---

## Proposed Shape

The clean shape is two-tiered:

### 1. Authored spec

A small declarative object stored on some carrier:

- node
- edge
- template payload
- content parser output

Possible fields:

- `label`
- `kind`
- `priority`
- `conditions`
- `locals`
- `tags`
- `media`
- `hides`
- `source_ref` or other authored selectors

This spec has no graph UID of its own.

### 2. Runtime binding

A lightweight bound view with context attached:

- `carrier`
- `subject`
- `caller`
- `source_id`
- merged or effective `locals`
- effective `tags`
- projected media or narrative annotations

Handlers then consume this binding without pretending it is a graph peer.

---

## Relationship to Existing Engine Layers

### Core / VM

The VM does not need a brand new universal "micro task" system to support the
useful parts of this idea.

The immediate path is to reuse existing handler surfaces:

- `on_gather_ns` for contextual property exposure
- planning / provisioning for dynamic provider-side affordances
- journal or content gather handlers for render projection

This is enough to support the first meaningful applications.

### Story

Story layer code is where microconcepts become narratively legible:

- roles grant titles and avatars
- affordances expose badge-like temporary status
- anonymous blocks or discovered providers may contribute contextual metadata
- block content can parse into dialog or card-like micro-blocks before render

### Discourse

Discourse parsing already has the clearest example of microconcept promotion:

`MuBlock -> Fragment`

That same promotion shape can later support:

- `MuAffordance -> BoundProviderView`
- `MuAffordance -> EffectiveTagOverlay`
- `MuAffordance -> Media projection`

---

## Preferred Implementation Strategy

### Phase 1: provider-bound grants

Start with the narrowest and most valuable slice from issue `#141`.

- Add edge-carried grant specs on story relationships such as `Role`
- Bind those grants to the currently resolved provider
- Expose them through namespace gathering as a contextual provider view
- Keep the grants derived, not persisted as mutable provider state

This solves the motivating examples:

- title
- rank
- badge
- avatar
- uniform

### Phase 2: effective overlay helpers

Add a small set of helpers for consuming bound microconcepts:

- effective locals
- effective tags
- effective media
- precedence / supersession ordering

This is the modern replacement for old dynamic badge mutation.

### Phase 3: relation to fanout

Allow planning-time created affordances to carry microconcept-like metadata that
binds to the selected provider.

This matters for:

- menu hubs
- sandbox hubs
- gathered provider choices
- future actor / location roster views

### Phase 4: evaluate common base with MuBlock

Only after the first two slices are working should StoryTangl decide whether
`MuBlock` and provider-side microconcepts want a shared base implementation or
just shared vocabulary.

The concept is shared already. The code does not need to be prematurely unified.

---

## What Should Not Be in Scope Yet

Issue `#113` bundled several larger ideas together. They should remain separate
from the first mu-affordance implementation:

- a universal heavy-task / light-task dispatch split
- a complete replacement of existing VM phase wiring
- global achievements or reactive rule engines
- generic enter / exit micro-dependency scripting
- persistent snapshotting of derived microconcept state

Those may later use the same vocabulary, but they are not required to realize
the main value here.

---

## Design Rules

### 1. Derived beats stored

If a property can be computed from current topology and current context, prefer
derived projection over mutating stored state.

### 2. Promote only when necessary

If something needs durable identity, inventory presence, or independent mutable
state, it should become a real Entity or Token. Otherwise it should remain a
microconcept.

### 3. Context is part of the contract

Microconcepts are not free-floating. The binding context is what makes them
meaningful.

### 4. Fragment remains output vocabulary

Do not overload "fragment" for provider overlays or relationship-bound grants.

### 5. Story semantics live above the generic layer

The generic layer should know about binding and projection. Story layer code
should know about titles, avatars, uniforms, badge text, and dialog speakers.

---

## Example Story Use Cases

### Role-linked title

```yaml
roles:
  - label: boss
    selector:
      has_kind: Actor
    grants:
      title: "boss"
      tags: ["management"]
```

While the role is bound, the namespace can expose:

- `boss`
- `boss_title`
- `boss.tags`

without mutating the underlying actor permanently.

### Role-linked avatar or uniform

```yaml
roles:
  - label: foreman
    selector:
      has_kind: Actor
    grants:
      media:
        - name: "foreman_uniform.svg"
          media_role: "avatar_im"
```

The assigned provider temporarily gains visual presentation metadata through the
role relationship.

### Dialog parsing

Authored block text can parse into `DialogMuBlock` items which later render into
attributed journal fragments, carrying speaker and discourse metadata without
turning each utterance into a graph node.

---

## Open Questions

- Should the generic implementation call these `MicroconceptSpec` /
  `BoundMicroconcept`, or use a more VM-neutral name like `AttachmentSpec` /
  `BoundAttachment`?
- Should bound provider views be proxy objects, plain mappings, or lightweight
  wrappers with explicit accessors?
- How should multiple active mu-affordances resolve conflicts for the same key:
  priority, scope, order of attachment, or explicit policy?
- Should effective tags become selector-visible everywhere, or only through
  specific helper paths?
- How much shared code should `MuBlock` and provider-bound microconcepts
  actually have, versus just sharing terminology?

---

## Proposed Near-Term Outcome

The near-term goal is not a giant "micro-behavior" subsystem.

The near-term goal is a clean way to represent **managed entity-like things with
less identity than Entities**, so StoryTangl can:

- bind temporary properties to providers through relationships
- carry small conceptual units through the VM without full graph registration
- parse authored content into structured intermediate units
- keep rendered fragments as the final output vocabulary

That would consolidate the useful core of issues `#113` and `#141` while
aligning with the old badge work and the already-working `MuBlock` pattern.
