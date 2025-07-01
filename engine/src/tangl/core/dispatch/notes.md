Core.Dispatch
=============

Each registry represents a _single_ process, with multiple handlers.  These can be interpreted as a single dispatch function, or as a _phased_ dispatch pipeline.

Each handler is registered with a _criteria_ for triggering; usually at least the caller's expected base class.  Scopes can be implemented by matching parts of the element's "path", i.e., "domain.graph.subgraph.node.element...".

There are several possible signatures for a handler:

`f(self/caller, *, ctx, other = None, result = None )`, mro instance methods, static methods
`f(self/owner, caller, *, ctx, result = None )`, instance methods on other nodes
`f(cls, caller, *, ctx, other = None, result = None )`, cls methods

Each type takes a variant of the register decorator and is added to a registry at different points.

In each case, they take a "caller" and the caller's context, and sometimes an optional "other" to operate on the caller or be operated on itself.  
If it is a pipeline-friendly method, it should also include a "result" input kwarg, and return a result object.

Call Receipts
-------------

"""
We have a partial graph, which has scoped data, shape, and behaviors.

At the resolution frontier, we can evolve the graph's data (effects) or shape (provisioning, journaling) using local (subgraph) or global/domain behaviors in "legal" ways (given predicates) to extend the resolution horizon.  Then we step out into it, note the activity trace (render content) and repeat.  We start from a source and eventually we will hit a sink and be done.

Along the way, we want to be able to inspect each evolutionary step, which behaviors were triggered, what shape and data changes resulted.
"""