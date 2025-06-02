`tangl.core`
============

Models and algorithms for an incremental, graph-based feature untangling framework

### Package Organization

```mermaid
flowchart RL
    subgraph .entity 
        Entity
        Registry -- is --> Entity
        Registry -- has --> Entity
        subgraph singleton_
          Singleton -- has --> Registry
          SingletonNode -- is --> Singleton
          SingletonNode -- is --> Node
        end
        subgraph graph_
            Graph -- is --> Registry
            Graph -- has --> Node
            Graph -- has --> Edge
        end
            
    end
    
    subgraph .handler
        Handler -- is --> Entity
        HandlerRegistry -- is --> Registry
        HandlerRegistry -- has --> Handler
        context_handler -- is --> HandlerRegistry
        effect_handler -- is --> HandlerRegistry
        predicate_handler -- is --> HandlerRegistry
    end

    subgraph .solver
        subgraph .abs_feature_graph
            AbsFeatureGraph -- is --> Graph
            AbsFeatureGraph -- has --> StructureNode
            AbsFeatureGraph -- has --> ResourceNode
            AbsFeatureGraph -- has --> JournalFragment
            AbsFeatureGraph -- has --> ControlEdge
            AbsFeatureGraph -- has --> DependencyEdge
            AbsFeatureGraph -- has --> BlameEdge
            
            StructureNode -- is --> Node
            StructureNode -- has --> ControlEdge
            StructureNode -- has --> DependencyEdge
            
            ResourceNode -- is --> Node
            ResourceNode -- has --> DependencyEdge
            
            JournalFragment -- is --> Node
            JournalFragment -- has --> BlameEdge
            
            ControlEdge -- is --> Edge
            DependencyEdge -- is --> Edge
            BlameEdge -- is --> Edge
            
        end
        subgraph .provisioner
            provision_handler -- is --> HandlerRegistry
            provision_handler -- uses --> DependencyEdge
            provision_handler -- builds --> ResourceNode
            provision_handler -- builds --> StructureNode
        end
        subgraph .render
            render_handler -- is --> HandlerRegistry
            render_handler -- builds --> JournalFragment
            Journal -- has --> JournalFragment
        end
        
        resolve_step -- has --> Journal
        resolve_step -- has --> AbsFeatureGraph
        resolve_step -- cursor --> StructureNode
        resolve_step -- calls --> context_handler
        resolve_step -- calls --> predicate_handler
        resolve_step -- calls --> effect_handler
        resolve_step -- calls --> provision_handler
        resolve_step -- calls --> render_handler
    end
```


### Tangled Feature Space

- Intermediate representation (IR) for a network of possible but unrealized interdependent features in superposition
- Declarative rules and constraints for realizing and modifying features, dependencies, initial state
- Use a self-evolving graph to incrementally satisfy constraints, identify or realize interdependencies, and discover control paths under a given control pattern
- The finalized graph provides a globally valid and stable configuration of "untangled" state and shape features for one possible lane through the space
- Trace of the control pattern moving through the graph provides an up-to-date linear history of the process

### Inspirations

- Bayesian Model Discovery (tangled prior and data → posterior inference → trace as posterior sample)
- Constraint Satisfaction and Logic Programming (nodes & dependencies → constraints & resolution)
- Software Package Dependency Resolution (dependency edges → abstract package reqs; resource nodes → concrete packages)
- Compiler & Intermediate Representation (tangled features → abstract IR; untangle -> interpreter; trace journal → trace IR)
