Plug-ins
========

StoryTangl uses the "Pluggy" plugin-manager developed for `pytest`.  Pluggy is a sophisticated, well maintained system.

There are a dozen world, story, and node life-cycle hooks where the plugin manager will try to call plug-in functions that can be defined in the story's world module.  Defining those functions and manipulating the return values can enable an author to implement a lot of interesting features without actually having to dig too much into the guts of the framework.

Plug-In Spec
--------------

.. autoclass:: tangl.world.story_plugin_spec.StoryPluginSpec
    :members:
