Redesign idea -- move ns from scope -> ctx, discover ns using handlers like any other task.

Issue: non-singleton domains should _not_ carry handlers, they will try to serialize them if they get attached to a graph, so we need a place for class instance handlers to live.

---

**Domains** are capability layers.  They have a `get_handlers(**criteria)` function and that's all.

Domains come in 3 (or more) flavors:

- Affiliate, opt-in explicitly noted by tag or other identifier on the anchor
- Structural, implicitly in the node's ancestor stack, ancestors are all structural domains
- Type-based, this is basically the same as explicit, but it is derived from the class mro, where handlers can be inferred from class or instance methods.  These are only considered if the class implements a `__get_handlers()` class method.

Domains plus an anchor node on a graph imply a *Scope*, the order and range of domains currently visible to the anchor.

**Scope**'s job is to merge domains and aggregate the results of `get_handlers(**criteria)` over all domains.

A **Context** is a graph, anchor, scope, namespace, along with some bookkeeping about jobs and results.

A context can compute the namespace at a given anchor by invoking `get_handlers(job=namespace)`, assembling the registered handlers across all domains, calling them, and aggregating the non-none results to a chain map.

Domains can participate in the namespace by defining a get_vars() func, which will be automatically discovered, or simply registering any other method on themselves with the job "namespace".

I like the idea of keeping namespace directly as a scope responsibility, but when you look at it this way, it seems clear that it should be in vm instead.  Scope -> discover and aggregate domain behaviors.  vm -> create a namespace by using scope to discover the domain behaviors for assembling a namespace and invoking them like any other phase.

This extends trivially to discovering domain-local templates, provisioners, anything else.  It only requires a single piece of bootstrap 'magic', which is knowing to use job="namespace" in the relevant handler registration.  No overloading `get_vars` or whatever.
