tangl.core
==========

Core architecture for the StoryTangl33 capability-based narrative engine.

StoryTangl33 reframes interactive fiction as a process of collapsing a latent 
capability-rich graph through a structured resolution protocol:

* **Requirements** pull structure into being from nodes, graphs, and domains
* **Capabilities** push effects, redirects, and media outward from these structures
* The **Cursor** iterates phases in a deterministic, auditable fashion
* A persistent **Journal** stores the narrative as rendered fragments

The StoryTangl33 architecture follows quantum narrative principles where the
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
* Context:          Scoped information gathering across graph tiers
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
    end

    subgraph graph_
        Node -- is --> Entity
        Node -- has --> Graph
        StructureNode -- is --> Node
        Graph -- has --> Node
        Graph -- is --> EntityRegistry
        Graph -- has --> Edge
        Edge
    end

    subgraph provision
        ResourceProvider -- is --> Entity
        ResourceProvider -- is --> Capability
        Template  -- has --> ResourceProvider
        Template -- builds --> Node
    end

   subgraph runtime
        HandlerCache  -- has --> Capability
        ProviderRegistry -- has --> ResourceProvider
    end
    
    subgraph resolver
        resolve --> Requirement
        resolve --> runtime
        resolve --> graph_
    end

    subgraph context
        ContextHandler --> Capability
        gather --> HandlerCache
        gather --> graph_
    end

    subgraph render
        RenderHandler --> Capability
        Fragment --> Entity
        Journal --> Fragment
        render_fragments --> Node
        render_fragments --> HandlerCache
        render_fragments --> Journal
    end

    subgraph cursor
        RedirectCap --> Capability
        ContinueCap --> Capability
        EffectCap --> Capability
        CursorDriver --> StructureNode
        CursorDriver --> resolver
        CursorDriver --> context
        CursorDriver --> render
    end
```

This design achieves clear separation between content structure, traversal
behavior, and presentation concerns while maximizing both extensibility
and performance predictability.
