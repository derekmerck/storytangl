Scripting
=========

There are a few different ways to format story scripts for ingestion.

Single-File Story Format
------------------------

Good for shorter, simpler scripts.  Everything is included in a single file.

.. literalinclude:: sfsf_example.yaml
   :language: yaml

.. automodule:: tangl.script.models
   :members:


Multi-File Story Format
-----------------------

Multi-file is good for longer, more complex scripts where the author wants to focus on individual sections while writing.

Multi-file story format uses the file directory to organize sections, one folder for each for <actors>, <assets>, <scenes>.  Within each folder, each yaml file is read as a multi-doc stream, and each individual document is merged into the appropriate script section.


Obsidian Notebook Format
------------------------

.. admonition:: In progress

Good for long-form writing where the author wants to keep notes and media in-line with the script content.

The Multi-file and Notebook format variants are pre-processed into Single-File Story format during loading.

It is fairly straight-forward to transform any consistently formatted data with the proper logical constructs (nodes, conditions, text blocks, etc.) into Single-File Story format for ingestion.

