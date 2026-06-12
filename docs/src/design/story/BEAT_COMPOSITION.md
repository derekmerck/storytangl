# Beat Composition

> Status: Current contract
> Authority: This note names the journal contribution pipeline alongside
> `JOURNAL_COMPOSE_CONTRACT.md`. The worked example is the
> `composed_beat_demo` world bundle and its loader test.

A journal step is a small **syuzhet** problem: the engine knows a set of
facts and consequences (the fabula), and the step's fragments are one
deliberate telling of them. The runtime already provides every channel that
telling needs; this note names them so mechanics and worlds compose beats
the same way instead of hand-rolling prose paths.

## The pipeline

One step's journal output is assembled in three moves:

**Gather.** `do_gather_ns` builds the scoped namespace: entity-local
`get_ns()` layers from the cursor and its ancestors (closest scope first),
then merged `gather_ns` dispatch contributions (later dispatch layers win).
Block content is rendered against this namespace with `format_map`, so any
named value — a *chunk* — is directly authorable as a `{placeholder}`.

**Enrich.** Extra fragments join the merged batch from two directions:
`render_journal` handlers contribute conditionally at render time, and
earlier phases (canonically UPDATE) stage delayed consequences through
`ctx.injected_journal_fragments`, which drain at the head of the merge.

**Compose.** `compose_journal` handlers fold over the merged batch in
dispatch order, each receiving the previous handler's output. This is where
the telling is shaped: reorder into slots, substitute what the viewpoint
cannot see, bind the result into a retrievable overlay.

## The override ladder

A named chunk can be defined — and overridden — at every scope, cheapest
first. Resolution order for a chunk read at the cursor:

1. **Block `locals:`** (authored YAML, no code)
2. **Ancestor `locals:`** — scene, then story containers, closest first
3. **`gather_ns` dispatch contributions**, merged later-wins across layers:
   AUTHOR beats APPLICATION beats SYSTEM; story-graph `locals:` beat world
   `locals:` within the story layer

Data overrides sit *above* handler overrides: an author writing
`locals: {dock_mood: ...}` on a block beats every registered handler. Use
data scopes for authored variation (skins, per-node mood) and handler
scopes for computed or stateful chunks.

A **narrative skin** is this ladder applied at presentation scale: one
selector chunk (`logic_skin` in `worlds/logic_demo`) chooses a sparse prose
overlay while the underlying machine stays untouched. Skins are a gather
concern (what the chunks say); beats are a compose concern (how the telling
is ordered). The two layers are orthogonal.

## The blessed stanzas

`tangl.journal.compose` names the recurring compose moves:

- `replace_first` — substitute the first fragment matching a predicate
  (the visibility/suppression move).
- `assemble_slots` — reorder the batch into named slots
  (`setting → incident → reaction → REST_SLOT` in the demo).
- `beat_overlay` — emit a `GroupFragment(group_type="beat")` whose
  `member_ids` bind the composed fragments and whose `content` names the
  beat. Segmentation-aware retrieval (`current_beat` style queries) slices
  on this overlay rather than re-deriving membership.

## Worked example

`worlds/composed_beat_demo` exercises every channel in one five-block
scene; `engine/tests/loaders/test_composed_beat_demo_world.py` pins one
channel per assertion. Mapping:

| Channel | Demo element |
| --- | --- |
| data-scope chunk override | `dock_mood` in story vs block `locals:` |
| handler-scope chunk override | `porter_greeting`, APPLICATION vs AUTHOR `gather_ns` |
| conditional render enrichment | Maro's reaction, gated on `reputation` |
| cross-phase enrichment | manifest incident injected during UPDATE |
| composition | slot ordering, fog substitution, beat overlay |

## Boundaries

Everything in `JOURNAL_COMPOSE_CONTRACT.md` applies unchanged: composition
shapes the telling, it does not mutate state, dereference media, or make
client-format decisions. Chunks are ordinary namespace entries — they are
visible to predicates, media facets, and dialog binding for free, so no
journal-private expression system should be introduced.
