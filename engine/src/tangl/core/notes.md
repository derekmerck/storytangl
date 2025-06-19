`tangl.core`
============

Models and algorithms for an incremental, graph-based feature untangling framework.

Entities can be attached to graphs or domains and register handlers for various functions that become available to subscribers in their scope.

Basic handlers include gathering a scoped context for a node, evaluating predicates and applying effects, and rendering output.

The solver evolves and grows the feature graph from a root node, maintaining a consistent, coherent state of local data and interdependencies.

### Package Organization

```mermaid
flowchart RL
    subgraph .entity 
        Entity
        Registry -- is --> Entity
        Registry -- has --> Entity
        subgraph .graph
            Node -- is --> Entity
            Edge -- is --> Entity
            Graph -- is --> Registry
            Graph <-- has --> Node
            Graph <-- has --> Edge
        end
        subgraph .singleton
            Singleton -- is --> Entity
            Singleton -- has --> Registry
            SingletonNode -- is --> Singleton
            SingletonNode -- is --> Node
        end
            
    end
    
    subgraph .dispatch
        Handler -- is --> Entity
        HandlerRegistry -- is --> Registry
        HandlerRegistry -- has --> Handler
    end
    
    subgraph .handler
        on_gather_context -- is --> HandlerRegistry
        on_apply_effects -- is --> HandlerRegistry
        on_apply_effects -- has --> RuntimeEffect
        on_check_satisfied -- is --> HandlerRegistry
        on_check_satisfied -- has --> Predicate
        on_render_content -- is --> HandlerRegistry
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
            on_provision_dep -- is --> HandlerRegistry
            on_provision_dep -- uses --> DependencyEdge
            on_provision_dep -- builds --> ResourceNode
            on_provision_dep -- builds --> StructureNode
        end
        subgraph .journal
            on_render_content -- builds --> JournalFragment
            Journal -- has --> JournalFragment
        end
        
        resolve_step -- has --> Journal
        resolve_step -- has --> AbsFeatureGraph
        resolve_step -- cursor --> StructureNode
        resolve_step -- calls --> on_gather_context
        resolve_step -- calls --> on_check_satisfied
        resolve_step -- calls --> on_apply_effects
        resolve_step -- calls --> on_provision_dep
        resolve_step -- calls --> on_render_content
    end
```


### Tangled Feature Space

- Intermediate representation (IR) for a space of possible but unrealized interdependent features in superposition
- Declarative rules and constraints for realizing and modifying features, dependencies, initial state
- Use a self-evolving graph to incrementally satisfy constraints, identify or realize interdependencies, and discover control paths under a given control pattern
- The finalized graph provides a globally valid and stable configuration of "untangled" state and affordances for one possible lane through the space
- Trace of the control pattern moving through the graph provides an up-to-date linear history of the process

### Inspirations

- Bayesian Model Discovery (tangled prior and data → posterior inference → trace as posterior sample)
- Constraint Satisfaction and Logic Programming (nodes & dependencies → constraints & resolution)
- Software Package Dependency Resolution (dependency edges → abstract package reqs; resource nodes → concrete packages)
- Compiler & Intermediate Representation (tangled features → abstract IR; untangle -> interpreter; trace journal → trace IR)
- Quantum wavefunction collapse (tangled features are in state of interdependent quantum superposition -> interpreter collapses space into a stable measurement)
