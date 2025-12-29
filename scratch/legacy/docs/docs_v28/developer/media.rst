Media Handler
=============

There are two fundamental concepts -- a `media reference` is a script element that eventually resolves to a concreate `media resource` file.  Media references are become media nodes in the story, then media nodes are 'rendered' by the service manager to discover or create the actual media resource.  Links to these resources are provided in journal entries, and then those files are served by a separate server.

Media references can either indicate pre-created files, or can provide a specification for creation of a file.  If the reference is fixed, the file becomes a static world resource.  If it is dynamic, it is created for a unique story and will be specific to a particular story's current state.

.. automodule:: tangl.media.media_node
    :members:


StableForge
-----------


SvgForge
--------


VoxForge
--------
