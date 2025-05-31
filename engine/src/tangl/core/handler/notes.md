Tangl.core.handler
------------------

Basic vocabulary for describing interactions of elements and state in the framework

**Handlers**
- Handlers are functions that can do named operations on an entity, given a context
- Handlers are themselves entities — they can be provisioned and collected in registries
- Handlers are typically called indirectly through a registry or collection of registries, either singly or in series and aggregated according to a strategy

**Context**
- A node-centric scoped view of the current _state_ of the system. 
- _ContextHandler_ is a specialized handler that gathers the context views used by any other handler type

**Predicates**
- Runtime entity gating given a context
- _Predicate_ is a wrapper for various means of evaluating satisfaction given a context
- _AvailabilityHandler_ is a specialized handler that can test whether a node both _matches_ criteria (shape) and _satisfies_ a predicate given a context (data) at runtime.

**Effects**
- Runtime entity actions upon a context
- _RuntimeEffect_ is a wrapper for various means of executing functions on a context
- _EffectHandler_ is a specialized handler that can apply effects at runtime