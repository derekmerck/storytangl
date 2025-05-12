tangl.core
==========

Core architecture for the StoryTangl capability-based narrative engine.

StoryTangl reframes interactive fiction as a process of collapsing a latent 
capability-rich graph through a structured resolution protocol:

* **Requirements** pull structure into being from nodes, graphs, and domains
* **Capabilities** push effects, redirects, and media outward from these structures
* The **Cursor** iterates phases in a deterministic, auditable fashion
* A persistent **Journal** stores the narrative as rendered fragments

The StoryTangl architecture follows quantum narrative principles where the
latent story space becomes concrete through observation (traversal) in a way
that prioritizes local causality over global state.

Package Organization
-------------------
* Entity:           Base data structure with identity and matching
* Registry:         Collection of entities with search utilities
* Graph:            Connected entities (nodes and edges) with traversal semantics
* Capability:       Phase-based computational units with tiered execution rules  
* Requirement:      Declarative expression of dependencies with resolution strategies
* Provision:        Dynamic providers that satisfy requirements
* StringMap:          Scoped information gathering across graph tiers
* Render:           Content projection to representation-agnostic fragments
* Cursor:           The driver of phased graph traversal and journal updates
* Resolver:         The system for matching requirements to providers

```mermaid
flowchart RL
    subgraph base 
        Entity
        Enums
        EntityRegistry -- has --> Entity
        Capability
        Requirement
        TierView
    end

    subgraph graph_
        Node -- is --> Entity
        Node -- has --> Graph
        Graph -- has --> Node
        Graph -- is --> EntityRegistry
        Graph -- has --> Edge
        Edge
    end

    subgraph provision
        ProviderCap -- is --> Entity
        ProviderCap -- is --> Capability
        Template  -- has --> ProviderCap
        Template -- builds --> Node
    end
 
    subgraph resolver
        resolve --> Requirement
        resolve --> graph_
        resolve --> TierView
    end

    subgraph context
        ContextCap --> Capability
        gather --> TierView
    end

    subgraph render
        RenderCap --> Capability
        Fragment --> Entity
        Journal --> Fragment
        render_fragments --> Node
        render_fragments --> Journal
        render_fragments --> TierView
    end

    subgraph cursor
        RedirectCap --> Capability
        ContinueCap --> Capability
        EffectCap --> Capability
        CursorDriver --> Node
        CursorDriver --> resolver
        CursorDriver --> context
        CursorDriver --> render
    end
```

This design achieves clear separation between content structure, traversal
behavior, and presentation concerns while maximizing both extensibility
and performance predictability.
