Core Concepts
=============

This section covers the fundamental building blocks of the StoryTangl engine.

1. :doc:`entity`
   Entities are the basic unit of data in StoryTangl, providing unique identification, labeling, and tagging.

2. :doc:`Graph and Node<graph_and_node>`
   Graphs, Nodes, and Edges extend Entity to support hierarchical and peer relationships, forming the backbone of the story structure.

3. :doc:`Mixins and Handlers<mixins_and_handlers>`
   Reusable components that add specific behaviors and functionality to Entities and Nodes.

4. :doc:`singletons`
   Single-instance objects that can be shared across graphs.

These core concepts work together to create a flexible and powerful system for representing and managing interactive narratives. Each concept builds upon the others, allowing for complex story structures and game mechanics to be implemented efficiently.

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Contents:

   entity
   graph_and_node
   mixins_and_handlers
   singletons