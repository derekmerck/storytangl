# StoryTangl Multi-Envelope Sequences

This directory contains JSON fixtures that exercise fragment-registry behavior
across more than one RuntimeEnvelope. Single-envelope fixtures prove that a
client can render one turn; sequence fixtures prove that a client can remember
fragments across turns and apply update/delete controls without losing decision
legibility.

Sequence files use this shape:

```json
{
  "sequence_id": "example",
  "description": "Short human note.",
  "envelopes": [
    { "cursor_id": "...", "step": 1, "fragments": [] }
  ]
}
```

Every envelope must validate as a `RuntimeEnvelope`. The sequence container is
intentionally lightweight and transport-neutral.
