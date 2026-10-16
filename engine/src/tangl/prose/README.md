# Prose: voices, concept names, and introductions

`tangl.prose` supplies narrative realization tools and optional Story extensions.
It turns authored text and scoped concept references into ordinary journal
fragments; it is not another story graph, client renderer, or fragment hierarchy.

Start with the [authoring guide](../../../../docs/src/design/story/PROSE_AUTHORING.md)
for examples, activation, anonymous naming, narrator knowledge, and escape hatches.
The code-adjacent [design contract](PROSE_DESIGN.md) specifies ownership,
ordering, persistence, and runtime linking in more detail.

`ProseBlock` remains the optional owner of ordered authored mu-blocks.
`ProseSegment` was replaced by that shared vocabulary. There is no active engine
`Voice` class: voice policy can currently use namespace helpers, named text-aspect
handlers, and explicitly configured `TextRenderSession`/Jinja environments.

The executable reference is
[concept_naming_demo](../../../../worlds/concept_naming_demo/README.md).
