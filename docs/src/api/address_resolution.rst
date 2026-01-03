Address Resolution
==================

The address resolution system provides a unified way to materialize
nodes at specific graph addresses using scope-based template selection.

Core Functions
--------------

.. autofunction:: tangl.story.fabula.address_resolver.resolve_template_for_address
.. autofunction:: tangl.story.fabula.address_resolver.ensure_namespace
.. autofunction:: tangl.story.fabula.address_resolver.ensure_instance

Usage Examples
--------------

Creating at Specific Addresses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from tangl.story.fabula.address_resolver import ensure_instance

    # Create typed instance at specific address
    shop = ensure_instance(
        graph=story_graph,
        address="village.market.shop",
        factory=world.script_manager.template_factory,
        world=world,
    )

    # Automatically creates namespace containers:
    # - village (Subgraph)
    # - village.market (Subgraph)
    # - village.market.shop (whatever template says)
