
This is the 'glue' that connects a story node to the sd image creator.

- story media script w path/url, media registry alias, or spec
- story media node is rendered
  - **path** is passed directly to the media fragment
  - **registry alias** is validated and the canonical id is passed to the media fragment
  - **spec** is transformed using an appropriate adapter for the parent node (actor, block, etc.) and its aliases are searched in the registry
    - if the spec alias is already in the media registry: pass
    - otherwise:
      - ask the spec what kind of creator it needs and invoke it
      - the spec may also be updated server-side with seed info or other random processes, so creators return a realized spec and associated media
      - register the returned media and update the node spec if the node is unrepeatable, otherwise leave it as the template so it can be re-rendered when the context is updated
      - provide the registered media record id in the media fragment

