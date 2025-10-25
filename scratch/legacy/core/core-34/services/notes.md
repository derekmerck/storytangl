`tangl.core.handlers`
--------------------

Basic vocabulary for describing interactions of elements and state in the framework

**Handlers**
- Base classes for Handler and HandlerRegistry are defined in `core.dispatch`
- Handlers are functions that can do named operations on an entity, given a context
- Handlers are themselves entities — they can be provisioned and collected in registries
- Handlers are typically called indirectly through a registry or collection of registries, either singly or in series and aggregated according to a strategy

**Context**
- A node-centric scoped view of the current _state_ of the system. 
- _HasContext_ is a specialized mixin that can gather context views to be used by other handler type
- The handler hook for gathering context is `_on_gather_context_`

**Predicates**
- Runtime entity gating given a context
- _Predicate_ is a wrapper for various means of evaluating satisfaction given a context
- _Satisfiable_ is a specialized mixin that can test whether a node both _matches_ criteria (shape) and _satisfies_ a predicate given a context (data) at runtime for gating
- The handler hook for checking conditions is `on_check_satisfied`

**Effects**
- Runtime entity actions upon a context after system creation
- _RuntimeEffect_ is a wrapper for various means of executing functions on a context
- _HasEffects_ is a specialized mixin that can apply effects at runtime
- The handler hook for applying effectes is `on_apply_effects`

**Rendering**
- Runtime entity output given context
- Based on templates by default, but amenable to other generation strategies
- _Renderable_ is a specialized mixin that can generate content fragments
- The handler hook for creating content is `on_render_content`
