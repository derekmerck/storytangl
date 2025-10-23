Domains and Namespaces
----------------------

**Domains** are capability layers.  They have a `get_handlers(**criteria)` function and that's all.

Domains come in 3 (or more) flavors:

- Affiliate, opt-in explicitly noted by tag or other identifier on the anchor
- Structural, implicitly in the node's ancestor stack, ancestors are all structural domains
- Type-based, this is basically the same as explicit, but it is derived from the class mro, where handlers can be inferred from class or instance methods.

Domains plus an anchor node on a graph imply a *Scope*, the order and range of domains currently visible to the anchor.

**Scope**'s job is to merge domains and aggregate the results of `get_handlers(**criteria)` over all domains.

A **Context** is a graph, anchor, scope, namespace, along with some bookkeeping about jobs and results.

A context can compute the namespace at a given anchor by invoking `domain.get_handlers(task=get_ns)` across all active domains and aggregating the results.

Domains will participate in the namespace by contributing their locals  by default, by registering any other method on their class with the job "get_ns".

This technique extends to discovering domain-local templates, provisioners, anything else.  It only requires a single piece of bootstrap 'magic', which is knowing to the name of the job in the relevant handler registration.

Issue: non-singleton domains should _not_ carry handlers, they _will_ try to serialize them if they get attached to a graph.
