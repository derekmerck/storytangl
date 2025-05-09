tangl.core.render
=================

Content projection from graph structure to presentation fragments.

The rendering system transforms abstract graph nodes into concrete
narrative fragments through:

- RenderHandler: Capability for generating fragments
- Fragment: Content carrier with text and media references
- Journal: Linear collection of fragments
- render_fragments: Core fragment collection algorithm

This system embodies the "narrative projection" aspect of StoryTangl's
quantum metaphor, where abstract story potential becomes concrete
realized content.

Rendering is representation-agnostic, producing structured fragments
that can be transformed into any presentation format (text, HTML, 
speech, etc.) by downstream clients.
