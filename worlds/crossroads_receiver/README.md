# Crossroads Inn: Receiver First

**Intent:** show ordinary receiver-authored calls to one shared conversation,
including an explicit scope guard and a destination-history `once` policy.
Compare [Sponsor First](../crossroads_sponsor/) for the same encounter with the
offer authored beside Aria. Both are near-native YAML; the distinction is where
the author organizes the relationship, not an imperative/declarative language split.

From the repository root, start `poetry run tangl-cli`, then enter:

```text
create_user crossroads-reader
run_script worlds/crossroads_receiver/cli_witness.txt
```

Or use `create_story crossroads_receiver` and choose freely. Aria's news unlocks
“Leave with the news.” Outside, the explicitly authored conversation Action
still exists, but its `bard` Role guard disables it. After the conversation,
its shared destination history disables the call at both inn receivers.

The [shared comparison and extension patches](../crossroads_sponsor/README.md)
show the actual additional Role, calls and navigation. The maintained Service,
JSON restore and CLI witnesses are linked there. They cover EAGER mutable shape;
they do not establish LAZY/JIT, frozen projection, REST, visual parity or general
client conformance.
