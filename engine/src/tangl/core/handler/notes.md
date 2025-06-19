`tangl.core.handler`
--------------------

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
- _AvailabilityHandler_ is a specialized handler that can test whether a node both _matches_ criteria (shape) and _satisfies_ a predicate given a context (data) at runtime for gating

**Effects**
- Runtime entity actions upon a context after system creation
- _RuntimeEffect_ is a wrapper for various means of executing functions on a context
- _EffectHandler_ is a specialized handler that can apply effects at runtime

----

Handlers can be:
1. Instance method on class/superclass of caller; invoked as
   `f(caller, ctx=ctx)`
2. Instance method on a different object that takes caller as arg; invoked as
   `f(owner, caller=caller, ctx=ctx)`
3. Class method on any class that takes caller as arg; invoked as
   `f(caller=caller, ctx=ctx)` (bc f is an already-bound class method)
4. Static (module-level) functions that take caller as arg

Any call will optionally pass along "other" (for comparison) and "results" (for pipelining) kwargs.

Handlers always want to be able to check in the caller has appropriate type; i.e.,
  `caller.match(has_cls=h.caller_cls)`

In case (1), caller cls is the same as owner cls
In case (2), caller cls must be named explicitly or use Entity to match any
In case (3), caller cls is either named explicitly or defaults to owner cls
In case (4), we must require an explicit caller cls

Cases 2 and 3 are considered 'promiscuous' b/c they will complete their binding against a caller that is not a subclass of the owner cls.

Owner and owner cls need to be inferred with each of the different registration patterns:

```python
class MyClass(Entity):

    @handler.register(...)
    def call_on_self(caller, ctx: dict, **kwargs) -> T: ...
    # can infer owner/caller cls from func name

    @handler.register(...)
    def call_on_owner(owner, caller, ctx: dict, **kwargs) -> T: ...
    # can infer owner cls but not caller cls from func name, need caller cls
    # explicitly and also need to hold the actual owner somehow, perhaps as a 
    # partial func?
    
    @handler.register(...)
    @classmethod
    def call_on_class(cls, caller: Entity, ctx: dict, **kwargs) -> T: ...
    # owner class could be inferred from fn, but is irrelevant since method 
    # is already bound to its class, need explicit caller cls

    @handler.mark_for_registration(...)
    def self_or_owner_or_cls_method(*args, **kwargs) -> T: ...
    
    def __init_subclass__(cls, **kwargs):
        # actually need this on super() or Entity, so this subclass calls it
        handler.register_marked_methods(cls)
        # have owner cls explicitly, need explicit caller cls

@handler.register(...)
def static_func(caller: Entity, ctx: dict, **kwargs) -> T: ...
# can't infer anything, no owner, need caller class explicitly
```
