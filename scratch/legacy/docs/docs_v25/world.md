
# World

A {class}`.World` object manages game object generation, manipulation, and inspection.  Each world surfaces a unique set of game entity subclasses, object type templates, and global variables.

The StoryTangl engine itself may have many game worlds available simultaneously and a player can maintain a state in all of them.

```{eval-rst}
.. automodule:: tangl.world.world
```

Worlds can also have special media handlers: {class}`Narrator` for text, {class}`Illustrator` for images, and {class}`Speaker` for vocal audio.  These helpers are mostly independent of the tangl story tree, and interface with individual nodes through adapter-mixins. All of these media helpers require _both_ preprocessing _and_ render-time co-routines.

## Narrator

The built-in Narrator uses a helper {class}`Prereader` to convert node text into a [jinja2][] markup that accounts for speaker roles and pronoun changes.  The prereader uses [spaCy][] and [Stanza][] to decompose the text, along with a number of other language related subroutines in `lang`, including conjugation, spelling, and grammar checking.

Then, at render-time, the Narrator evaluates the templates for each piece of story text to update for the particular current story-state.

[spacy]: https://spacy.io/
[stanza]: https://stanfordnlp.github.io/stanza/
[jinja2]: https://jinja.palletsprojects.com/en/3.1.x/

```{eval-rst}
.. automodule:: tangl.world.narrator.narrator
.. automodule:: tangl.world.narrator.prereader
.. automodule:: tangl.world.narrator.lang
.. automodule:: tangl.story.narrated
```

## Illustrator

The built-in Illustrator handles `svg` media with its helper {class}`.SvgForge` and can create and manage AI-generated `png` with its helper {class}`.StableForge`.

Illustrated material is generally produced dynamically from a `Spec` class that is unique to the modality.  The `Illustrated` mixin class is generally responsible for providing a spec that bridges from story to illustration.

```{eval-rst}
.. automodule:: tangl.world.illustrator.illustrator
.. automodule:: tangl.story.illustrated
```

### StableForge

```{eval-rst}
.. autoclass:: tangl.world.illustrator.stableforge.StableForge
.. autoclass:: tangl.world.illustrator.stableforge.StableSpec
```

### SvgForge

This is SvgFactory vers 2.0, somewhat streamlined and simplified

Scene images and avatars for StoryTangl....

```{eval-rst}
.. autoclass:: tangl.world.illustrator.svgforge.SvgForge
.. autoclass:: tangl.world.illustrator.svgforge.SvgDesc
```

### Avatar

`Avatar` an extension to {.class}`SvgForge` that generates a dynamic image of a game character, accounting for *pose* and *look* parameters.

```{eval-rst}
.. autoclass:: tangl.story.actor.avatar_mixin.AvatarMixin
.. autoclass:: tangl.world.illustrator.avatar.Avatar
```

## Speaker

The built-in `Speaker` can create and manage AI-generated audio voice over.

```{eval-rst}
.. automodule:: tangl.world.speaker
.. automodule:: tangl.story.spoken
```


