# Crossroads Inn: Sponsor First

**Intent:** show Aria offering one owned conversation to ordinary receiving
blocks through an actual shared Role and structural scene requirement. Compare
[Receiver First](../crossroads_receiver/), which authors the calls at each site.
Both use near-native YAML; receiver-first and sponsor-first describe authoring
organization, not different programming languages.

From the repository root, start `poetry run tangl-cli`, then enter:

```text
create_user crossroads-reader
run_script worlds/crossroads_sponsor/cli_witness.txt
```

Or use `create_story crossroads_sponsor` and choose freely. Aria's news unlocks
“Leave with the news.” The hearth and table expose Aria through their scene's
`bard` Role. The yard has no such exposure: its graph has no projected Aria
Action, even though Aria exists in the world. The receiver-first yard retains
an explicit but disabled guarded Action. Once the conversation is consumed,
both inn projections remain attached but unavailable.

## Actual authoring changes

The shipped sponsor-first conversation adds this to the owned Scene; neither
receiver has an Aria call:

```yaml
offer:
  source_requirement: {has_tags: [crossroads_inn]}
  once: true
```

Receiver-first instead puts this call at the hearth, table and yard (the yard's
guard deliberately refuses):

```yaml
- successor: aria.conversation
  return: true
  once: true
  conditions: ["'bard' in roles"]
```

Both worlds declare the same `bard: {actor_ref: aria}` at the inn. The Role is
necessary scope wiring; a catalog Actor alone is not an exposure. Both use the
Scene's `action_name` and the same graph-local news effect.

The maintained extension experiment starts with these shipped files and adds
Bram plus a porch in either order. Its actual patches add the following:

```yaml
# Both versions: actor, shared scene Role, and two navigation links
actors:
  bram:
    name: Bram
    episodes:
      conversation:
        action_name: Ask Bram about the bridge
        blocks:
          message: {content: Bram says the bridge is sound.}
scenes:
  inn:
    roles:
      bram: {actor_ref: bram}
    blocks:
      hearth:
        actions:
          # appended to existing actions
          - {text: Walk to the porch, successor: porch}
      porch:
        content: The porch is sheltered from the rain.
        actions:
          - {text: Return to the hearth, successor: hearth}
```

In sponsor-first, Bram's conversation also gets the same `offer` shape above;
no conversation Actions are added to the existing receivers or porch. In
receiver-first, adding Bram appends the following explicit call at hearth,
table and yard; if the porch already exists it gets the call too. Adding the
porch appends Aria's guarded call and, if Bram already exists, Bram's call:

```yaml
- successor: bram.conversation
  return: true
  once: true
  conditions: ["'bram' in roles"]
```

Thus Bram requires one actor/episode and one shared Role in both versions; the
receiver-first patch additionally has three explicit calls for the baseline
sites, or four if the porch already exists. The porch requires one block and two
navigation links in both; receiver-first adds one or two conversation calls
according to whether Bram has already been added. These are counts for these
actual patches, including the out-of-scope control, not a general complexity
formula. Both construction orders are executed and compared semantically.

## Maintained evidence and limits

The shipped bundles are loaded by normal discovery and Service creation. The
[Service/JSON tests](../../engine/tests/loaders/test_crossroads_authoring.py)
use emitted choice IDs, exercise both actual callers, shared consumption,
outside scope, JSON restoration and extension orders. The [CLI tests](../../apps/cli/tests/test_world_cli_witnesses.py)
run both world-owned scripts through the cmd2 CLI and surface command errors.
These are local Service and CLI witnesses for [#438](https://github.com/derekmerck/storytangl/issues/438),
not evidence of REST, media, visual parity or universal conformance.

The supported projection is EAGER and mutable. LAZY/JIT and frozen projection,
Role-owned episodes, richer invocation context, Fire Aria and return policy,
and sandbox consumer convergence remain follow-ups under
[#702](https://github.com/derekmerck/storytangl/issues/702) and
[#255](https://github.com/derekmerck/storytangl/issues/255).
