# Where Narrative Control Lives

```{storytangl-topic}
:topics: traversal, prose, open_link
:facets: design
:relation: documents
:related: provisioning, sandbox, journal
```

> **Status:** GUIDANCE. This is a rule for choosing how to represent a narrative
> distinction, not a contract for any one mechanism.
>
> **Neighbouring notes:**
> - [philosophy.md](philosophy.md) gives the conceptual rationale.
> - [AFFORDANCE_MODEL.md](../planning/AFFORDANCE_MODEL.md) defines the mechanics of the dynamic level.
> - [CONCEPT_LINKED_PROSE.md](CONCEPT_LINKED_PROSE.md) covers concept references inside rendered prose.

---

StoryTangl deliberately lets the same narrative behavior be expressed at
several semantic levels:

- a conditional line of prose;
- a conditional branch in the graph;
- an affordance that a concept contributes at runtime.

For one traversal, all three may produce indistinguishable journals. They
differ in three things:

- what the engine knows about the distinction;
- how independently the distinction can evolve;
- whether the structure exists before runtime.

No rule says a variation belongs at the most elaborate level available. The
right level depends on what the story needs to know, preserve, query, or
extend.

## Presentation control

The lightest representation is control inside presentation. Block text is
rendered at journal time, through `str.format_map` or Jinja, so a single block
can do any of these:

- add a line for an actor who happens to be present;
- choose among descriptions by current state;
- name someone differently once they have been introduced.

Structurally, the same block was visited whichever words rendered.

This suits a distinction that matters only to the current presentation. It is
cheap, compact, and often easier to read than a graph with a node for every
possible sentence.

The cost is that a presentation decision leaves little semantic residue. The
journal keeps the words that rendered, so it can answer "was this block
visited?" It cannot answer "which condition chose these words?" Current state
may not answer it either, since the state that governed the rendering may have
changed since. Recovering the distinction means preserving the render context,
or promoting the variation into a more explicit record.

That is not inherently a problem. If no later mechanic, callback, analysis, or
replay policy needs to tell the variants apart, recording the difference adds
complexity and buys nothing.

## Static semantic control

A variation can instead be explicit in the graph's structure: separate blocks,
conditional edges, calls and returns, branches that rejoin. Each beat becomes
an independently identifiable part of the episodic process.

This costs more structure and buys provenance:

- visit history can show directly that a particular beat occurred;
- effects can attach to the beat;
- other story elements can depend on it, reorder it, redirect around it, or
  query it later.

Static structure is also extensible. Consider a finale in which a landlord's
inspection meets whichever of three known tenants are home. Their reactions
could be three Jinja branches inside one large scene. They can instead be
three independent conditional blocks on a common path:

```text
the landlord arrives
    ↓
Ada interaction?   → return
    ↓
Bram interaction?  → return
    ↓
Cleo interaction?  → return
    ↓
collective response
```

This makes each interaction addressable on its own, and makes the topology
itself editable. A new beat goes in without rewriting an `if/elif` tree inside
a monolithic template.

This is often worth doing even where dynamic provisioning would be cleaner in
theory. A known, closed cast can be represented explicitly and still keep most
of the practical benefit of semantic decomposition.

## Dynamically provisioned semantic control

At the most open-ended level, the graph need not contain every possible
interaction in advance. Concepts present in the current context make *scoped
contributions*: they contribute their own affordances, episodes, effects, or
discourse enrichments. Planning discovers which contributions are currently
satisfiable and projects them into the local story.

The host no longer needs exhaustive knowledge of its participants.

- **A sandbox location** doesn't need code saying that Aria can sing if she is
  in the party, that the clockmaker can repair equipment when he is in his
  workshop, and that every future character has some other special interaction.
  Aria carries the affordance that lets her sing. The clockmaker carries the
  repair affordance and its contextual requirements. Presence, location,
  inventory, relationships, and other concepts supply the namespace in which
  those affordances become available.
- **A landlord story** doesn't need the building to own an encyclopedia of every
  tenant's story. A tenant can carry their own episode progression, and
  contribute the next applicable beat when their state and the local context
  make it relevant.

The inspection finale above can be generalized the same way:

1. Discover every concept satisfying `Tenant`.
2. Let each contribute an inspection interaction.
3. Run the applicable contributions.
4. Collect the semantic enrichments from those encounters for a final,
   aggregate response.

Adding a tenant then needs only two things: a path by which a character can
become a tenant, and the interactions or enrichments expected of that concept.
The finale itself is never reopened.

This is more than dynamic branching. It changes where narrative authority
resides:

- the world or location supplies context;
- concepts supply potential behavior;
- planning determines what can presently exist;
- traversal turns that resolved possibility into journaled discourse.

## Choosing a level

These representations are not stages of architectural maturity. A Jinja
conditional is not an inferior graph branch, and a static branch is not an
unfinished provisioned affordance. They answer different questions:

| Level | Question |
|---|---|
| Presentation control | Which words should render? |
| Static semantic control | Which authored beat happened? |
| Dynamic affordance control | Which beats should exist here, given the concepts now participating? |

**Use the lowest semantic level that preserves the behavior the story actually
needs.**

Promote presentation variation into graph structure when the distinction needs
any of these:

- independent provenance;
- effects;
- dependencies;
- callbacks;
- ordering;
- testing;
- structural extensibility.

Promote static structure into dynamic provisioning when the variability is
itself part of the domain model. That is especially the case when concepts
should stay portable, and new participants should be able to contribute
behavior without modifying a central host.

Conversely, don't manufacture graph nodes because a sentence *could* someday be
queried. Don't build a resolution protocol because three explicit conditional
blocks could in theory be generalized.

The architecture should preserve an upgrade path between these
representations, without requiring authors to take it prematurely.

That matters because the most general formulation is seductive. Once a scene
can be imagined as planning that composes behavior from arbitrary concepts, an
explicit branch or a Jinja conditional can look philosophically impure. In
practice, an expedient static implementation may be clearer, safer, and
entirely correct. That is especially true of artifact-constrained stories, such
as adaptations of fixed source material, where the cast and the possibilities
are already known.

Semantic sophistication should therefore be demand-driven. The goal is not to
maximize dynamism. It is to place narrative control at the level where its
meaning needs to exist.
