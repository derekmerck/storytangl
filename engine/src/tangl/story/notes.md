

Every story node "class" needs 2-3 things:

1. A data model, this is the keywords that could be in a script yaml document to create/deserialize it
2. A set of flexible/plugable handlers for instances of the class that trigger on different events:
  - new(base cls, kwargs, domain) -> (new cls, new kwargs)     # No context
  - init -> None                                               # No context
  - gather locally scoped context -> dict
  - find or create/render media or narrative content -> content dict (direct or indirect - content/blob id)
  - follow an edge -> None  (do an action)
  - visit/enter a node -> next node or None
  - check conditions, availability -> Any, bool
  - apply effects -> bool
  - associate with another node -> None
  - find or create an associate -> Associate
3. Content creators that know how to generate content for a node content spec, register blobs if required, and return a content dict for a node 
4. Adapters that know how to convert different types of content dicts into appropriate narrative or media journal fragments
5. An adapter that knows how to convert a graph or node into an info model