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