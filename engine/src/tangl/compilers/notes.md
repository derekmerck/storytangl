
This subpackage organizes the script compilers.

The script manager itself uses a consistent format for story graph templates, breaking them up into concepts and structure nodes.

A script manager can be _created_ from various pre-processors, from trivially reading yaml files directly into script manager elements, to functional definitions that infer a script based on dependencies and content chunks.

The script manager is one of the 3 key domain controllers, along with an asset manager and plugin manager, that make up a new story world.
