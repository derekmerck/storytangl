Story Compilers
===============

This subpackage organizes the story compilers.

The script manager itself is a registry of templates in a simple, serialized format that that can be instantiated into a new graph using Entity's built-in structure function.

The templates can be _created_ using various pre-processors, from trivially reading yaml files of node parameters, to functional definitions that infer concepts and structure elements based on dependencies and content chunks.

The script manager is one of the 3 key domain controllers, along with an asset manager and plugin manager, that make up a new story world.
