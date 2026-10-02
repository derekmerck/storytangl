# StoryTangl Worlds

The worlds in this directory are a teaching collection, not a ladder of
increasingly complete games. They are organized by the kind of idea an author
is likely to be looking for: first an ordinary StoryTangl world, then isolated
mechanics, then compositions that produce recognizable game grammars, and
finally architectural proofs and adapters.

Reader-facing titles are allowed to be memorable; directory names and manifest
labels are the stable machine identifiers.

The descriptions below state **intent**. They do not imply that every possible
client, persistence path, or integration surface is currently exercised for
every world. The maintained conformance classification is tracked separately in
[#438](https://github.com/derekmerck/storytangl/issues/438). The catalog work
itself is tracked in
[#461](https://github.com/derekmerck/storytangl/issues/461), and the distinction
between focused fixtures, conformance worlds, and showcase stories is described
in [#395](https://github.com/derekmerck/storytangl/issues/395).

## Start Here

### [The Crossroads Inn](reference/) — `reference`

**Role:** author-facing tutorial.

A deliberately ordinary near-native YAML world: scenes contain blocks, blocks
offer choices, one actor is templated, and media is optional. Nothing in this
world is meant to be clever. Copy it when you want to see the smallest
recognizable StoryTangl story bundle before adding a mechanic.

## Small Pieces: One Mechanic at a Time

These worlds keep the surrounding fiction thin so the reusable interaction
shape stays visible.

| World | What it isolates | Good starting point when... |
| --- | --- | --- |
| **Three Hands at the Tavern** (`rps_tavern`) | A minimal Rock-Paper-Scissors `HasGame` encounter inside an ordinary story shell. | You want one compact competitive game block. |
| **The Contest Pit** (`bag_rps_pit`) | Bag-RPS: commit a reserve of force and deplete an opponent. | You want a contest over aggregate resources rather than one symbolic move. |
| **The Back-Room Table** (`blackjack_parlour`) | One narratively loaded hand of blackjack. | You want a card-game kernel embedded in traversal. |
| **The Silver Thimble** (`kim_tray`) | Observation, retention, and recall over a small object set. | You want a memory/recognition interaction. |
| **The Salvage Yard** (`incremental_yard`) | Repeated re-entry, accumulation, and cycle resolution. | You want a small incremental/planning loop. |
| **Night Shift** (`ed_queue_demo`) | A deterministic discrete-event queue simulation that reports through normal journal fragments. | You want simulation state to participate in a story without a second runtime. |
| **[Fogbound Manifest](composed_beat_demo/)** (`composed_beat_demo`) | Journal gather → enrich → compose, including cross-phase contribution and post-merge assembly. | You want to control how several semantic contributions become one narrated beat. |

## Game Recipes: Familiar Flavors from Ordinary StoryTangl Parts

These are compositions rather than new runtimes. The comparisons below describe
**mechanical flavor and organizational lineage**, not content adaptation.

| World | Mechanical recipe | Presentation / interaction lesson |
| --- | --- | --- |
| **[The Checkpoint](credential_gate/)** (`credential_gate`) | Inspection and disposition in the tradition of *Papers, Please*: examine evidence against rules, then rule on the case. | Structured credential packets, inspection, mediation, and disposition over the shared credentials mechanic. |
| **[Hall Monitor](hall_monitor/)** (`hall_monitor`) | The same credentials evaluator under school vocabulary, with a recurring bearer and delayed world-authored consequence. | Shows that the mechanic is semantic rather than checkpoint-specific: the same packet/disposition lifecycle projects into a very different fiction. |
| **[Coronate the Regent](coronate_the_regent/)** (`coronate_the_regent`) | Preparation under a fixed schedule in the tradition of *Long Live the Queen*: train now, discover much later which earlier choices mattered. | Ordinary journal and optional scene art carry a mechanically richer loop without requiring a special client. |
| **Grand Grotto** (`adventure_sandbox_slice`) | A *Colossal Cave*-style spatial adventure slice: locations, inventory, light, locks, darkness, and projected affordances. | The text UI can disguise the current typed choice frontier as completable command phrases, producing a parser-like interaction without a second parser runtime. |
| **[One Red Paperclip](red_paperclip/)** (`red_paperclip`) | A one-slot barter and route-planning puzzle over a graph of traders and holdings. | The same semantic choices work as CLI rows or pygame map hitboxes; the world also has its own graph-analysis tooling. |
| **Hungry Colony** (`colony_loop`) | Production → force conversion → raid → attrition/reward fed back into the production shell. | Demonstrates composition: two small kernels constrain the same durable state instead of appearing as disconnected minigames. |
| **[Marmoset Island](repartee_loop/)** (`repartee_loop`) | A battle-of-wits loop in the tradition of *Monkey Island*: lose to learn a response, retain it, recognize the matching call later, and reuse it. | CLI floor plus pygame map, staged sprites, animation, and a swappable visual reskin. The alternate art pack is **Marmoset Orbital Station**: the graph, prose, choices, and staging semantics stay the same while the presentation changes. |

## Advanced: Architecture, Authoring Adapters, and Foreign Hosts

These examples are not “my first game” templates. They probe how far the same
runtime model can be pushed or approached from a different authoring or
presentation environment.

| World | Question it answers |
| --- | --- |
| **[Loomworks](logic_demo/)** (`logic_demo`) | Can authored graph topology and traversal perform computation without handing arbitrary code to `exec`/`eval`? The world contains parity, half-adder, and full-adder machines plus a sparse narrative skin over the same topology. |
| **The Ruined Tower** (`twine_reference`) | Can a small Twee/Twine story be consumed as foreign source and compiled into the ordinary StoryTangl runtime graph? |
| **[Twine Logic Demo](twine_logic_demo/)** (`twine_logic_demo`) | A secondary parity fixture for the same codec path. It is useful for authoring-format parity, but is not the recommended first Twine example. |
| **Ren'Py Demo** (`renpy_demo`) | Can Ren'Py act as a foreign presentation host while StoryTangl remains the narrative backend? The current world is intentionally still a compact adapter proof and is due for a more coherent vignette/art pass. |

The advanced trio is deliberately asymmetric:

```text
foreign authoring                    foreign presentation host
      Twee/Twine  ->  StoryTangl  ->  Ren'Py
                          |
                          +-> Loomworks: the graph itself as a machine
```

## Choosing an Example

If you are writing your first world, copy **The Crossroads Inn**.

If you need one reusable interaction, start from the smallest world that isolates
it. If you are trying to reproduce the *feel* of a known game structure, look at
the recipe worlds and ask which durable state and mechanics create that flavor.
If you are changing source formats or clients, start in the advanced section.

A strong demo does not need to exercise every StoryTangl feature. Its job is to
make one useful idea unusually easy to see.

## Minimal Bundle Shape

Near-native worlds conventionally look like:

```text
my_world/
├── world.yaml
├── script.yaml
└── media/          # optional
```

A minimal manifest is:

```yaml
label: my_world
metadata:
  title: "My Story"
scripts: script.yaml
```

For alternate codecs, domain modules, multi-story anthologies, or custom media
inventory, use the nearest example above rather than growing the beginner world
into an omnibus template.

World discovery, runtime startup, and client commands are documented in the
repository [README](../README.md). New demo worlds should state their intent
clearly and should not claim integration surfaces their maintained witnesses do
not actually exercise.
