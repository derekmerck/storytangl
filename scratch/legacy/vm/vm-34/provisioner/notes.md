Provisioning
------------

### Terms

- **Dependency**: An edge from a "needer" node that requires something, to a "provider" node that satisfies the requirement.
- **Affordance**: The inverse edge of a dependency, from the provider node back to the needer.

- **Forward Provisioning**: Given a structure node, discover or create resource nodes to fulfill its outgoing dependencies.
- **Backward Provisioning**: Given a node, discover or create nodes to fill required affordances, ensuring the current node is used in the graph.

**Forward resolution** relies primarily on incremental forward provisioning at the resolution frontier and backwards provisioning for _critically required_ nodes given a particular control path.