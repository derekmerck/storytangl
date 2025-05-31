tangl.core
==========

Core architecture for the StoryTangl capability-based narrative engine.

StoryTangl reframes interactive fiction as a process of collapsing a latent 
capability-rich graph through a structured resolution protocol:

* **Requirements** pull structure into being from nodes, graphs, and domains
* **Capabilities** push effects, paths, and narrative content outward from these structures
* The **Cursor** iterates phases in a deterministic, auditable fashion
* A persistent **Journal** stores the narrative as rendered fragments

The StoryTangl architecture follows quantum narrative principles where the
latent story space becomes concrete through observation (traversal) in a way
that prioritizes local causality over global state.

Package Organization
-------------------
* Entity:           Base data structure with identity and matching
* Registry:         Collection of entities with search utilities
* Capability:       Phase-based computational units with tiered execution rules  
* Graph:            Connected entities (nodes and edges) with traversal semantics
* Provision:        Dynamic provider resolution to satisfy declarative requirements
* Context:          Scoped environment gathering across organizational tiers
* Render:           Content projection to representation-agnostic fragments
* Cursor:           The driver of phased graph traversal and journal updates

```mermaid
flowchart LR
    subgraph base 
        Entity
        Registry -- has --> Entity
        Capability
        TierView
    end

    subgraph graph_
        GlobalScope -- is --> ScopeMixin
        Domain -- is --> ScopeMixin
        Graph -- is --> EntityRegistry
        Graph -- is --> ScopeMixin
        Graph -- has --> Node
        Graph -- has --> Edge
        Node -- is --> Entity
        Node -- is --> ScopeMixin
        RedirectCap --> Capability
        ContinueCap --> Capability
    end

    subgraph provision
        Requirement
        ProviderCap -- is --> Entity
        ProviderCap -- is --> Capability
        Template  -- has --> ProviderCap
        Template -- builds --> Node
        resolve_reqs --> ProviderCap
        resolve_reqs --> Requirement
        resolve_reqs -- builds --> Node
        resolve_reqs --> TierView
    end
 
    subgraph context
        ContextCap --> Capability
        gather_context --> TierView
        gather_context --> ContextCap
    end

    subgraph render
        RenderCap --> Capability
        Fragment --> Entity
        Journal --> Fragment
        render_fragments --> Node
        render_fragments --> RenderCap
        render_fragments -- builds --> Fragment
        render_fragments --> Journal
        render_fragments --> TierView
    end

    subgraph cursor
        EffectCap --> Capability
        CursorDriver --> Node
        CursorDriver --> resolve_reqs
        CursorDriver --> gather_context
        CursorDriver --> render_fragments
        CursorDriver --> RedirectCap
        CursorDriver --> ContinueCap
        CursorDriver --> EffectCap
    end
```

This design achieves clear separation between content structure, traversal
behavior, and presentation concerns while maximizing both extensibility
and performance predictability.
