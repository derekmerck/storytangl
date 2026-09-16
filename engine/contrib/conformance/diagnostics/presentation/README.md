# Presentation realization diagnostic

Status: experimental comparison for issues #457 and #454. Nothing in this
directory defines a production fragment, persistence, `render_str`, HTML, or
terminal contract.

Run:

```bash
poetry run python engine/contrib/conformance/presentation_realization_demo.py
```

The two files under `authored/` are the author-facing inputs. The generated
`realization_report.json` keeps the boundaries together for inspection:

1. literal authored Jinja plus Pandoc-like block/span markup;
2. authoring-adapter output after template evaluation and the tiny local parser;
3. the renderer-neutral fragment DTO candidate;
4. structural, escaped HTML;
5. Rich span inspection and plain/`NO_COLOR` output without canonicalizing raw
   ANSI bytes.

The diagnostic uses the real fragment models, `RuntimeEnvelope.to_dto()`, and
the current Jinja evaluator. Its `content: {text, spans, offset_unit}` value is
deliberately local. The parser accepts exactly one Pandoc-like classed block and
flat classed inline spans. Adjacent spans are supported; nested, overlapping,
unclassed, or malformed spans fail. This is an executable specimen, not a
proposed author grammar. An Obsidian-admonition-to-Pandoc preprocessing step is
not exercised or proved.

`ContentFragment.content` currently accepts `Any`, but that permissiveness is
not a discriminated public attributed-text contract and current clients
generally assume a string.

## Two independent dimensions

Presentation does not require one universal projection mechanism. The
experiment separates two choices that can vary independently:

- **Projection resolution** is the sampling density from the parameterized
  episodic spine and recruited concepts onto the visible interactive surface:
  a coarse episode gloss or generative specification; typed fragments at the
  current middle; individual utterances and annotated spans; or fully
  tessellated renderer-near nodes. Higher density simplifies deterministic
  consumers but increases backend computation, identity, persistence, and
  stream-management cost. Lower density delegates interpretation and can drift
  from authored causality.
- **Realization binding** is how a projected disclosure travels or renders:
  renderer-neutral typed JSON or annotated text; a bounded syntax such as
  Markdown; class-tagged or styled HTML; or adapter-local Rich/ANSI primitives.
  Mechanic transport is related but distinct: mechanics establish authoritative
  visible state and interactions, while presentation chooses how densely that
  state and narrative content are sampled and linearized.

The generated report records these concrete points:

| Projection resolution | Realization binding | Position | Cost, expressiveness, and replay |
| --- | --- | --- | --- |
| Middle, typed fragments | Renderer-neutral typed JSON | Durable supported floor; both bundles start here | Bounded identity count, current reachability, provenance, and causal plus semantic replay |
| Fine, attributed utterance/spans | Neutral text plus annotations | Experimental refinement in `prose-dialog` | More boundaries and validation; deterministic consumers retain semantic text and can ignore unknown refinements |
| Fine to tessellated | Classed HTML or adapter-local Rich primitives | Supported deterministic derivation | More consumer work and renderer detail; exact historical rendition is not promised |
| Coarse typed gloss or generative specification | Nondeterministic client refinement, such as an LLM | Valid extreme, not implemented | Cheap backend projection and possible variation; replay repeats the stored packet, not the old client result |

The supported target is a range with a durable floor: stable fragment/action
identity and provenance; a canonical replayable semantic or procedural packet;
offered action identity and current reachability; and type-defined fallback or
unsupported-type diagnostics. This mixed packet intentionally proves only the
choice fields recorded in its structural manifest. The sibling
`engine/contrib/conformance/parity.py` harness owns blockers, typed `accepts`,
`ui_hints`, activation payload, and portable submission coverage. Existing
fragment types retain their current readable fallbacks. A future typed
procedural or generative fragment need not pretend its final generated text is
journal authority.

Three replay promises must remain distinct:

1. **Graph/causal replay** restores the semantic story state from the graph
   delta/checkpoint stack, including accepted actions and state changes.
2. **Journal/projection replay** walks the journal registry's ordered records
   to recover the stored fragment/event stream, whether a record carries
   concrete annotated text, structured JSON for a service, or a media or
   procedural request.
3. **Exact rendition replay** would preserve final text, pixels, audio, model
   and seed receipts, or generated assets. That is an optional archival/audit
   feature, is not currently promised, and remains out of scope.

Capable clients may realize less, more, or differently than the journal packet.
Deterministic HTML/Rich derivation and nondeterministic LLM rewrites, on-demand
TTS, maps, or similar enrichment may all remain ephemeral. Replaying the journal
does not require returning those client results to journal authority.

The authority chain is therefore explicit:

1. The graph delta/checkpoint stack is replayable semantic story state.
2. JOURNAL is the deterministic backend projection over the evolving graph,
   current cursor, recruited concepts, namespace, and registered handlers.
3. The journal registry stores its ordered linearization; walking the registry
   recovers the fragment and event stream sent toward clients.
4. Transport packages those records for a client without defining final
   rendition.
5. Client rendering and interaction presentation are client policy. A client
   may omit, rearrange, enrich, or vocalize content, but only accepted actions
   and resulting state changes become backend authority.

The current JOURNAL phase already assumes a shared feature vocabulary. The
design question is how broad, flexible, deterministic, and capability-aware
that projection vocabulary should be, not how to preserve one final rendition.
Each emitted fragment kind defines its own minimum interpretation and fallback
or unsupported-type behavior. Reference clients should completely realize the
supported public fragment and interaction vocabulary with documented fallback.
Third-party clients may consume a strict subset or derive richer output without
making their private interpretation authoritative.

A prose-blind bot marks the subset boundary. It may ignore prose and media,
consume only cursor/current-state projections and offered action identities,
choose among those actions using its own model, and submit through the normal
action contract. If authorized, it may consult additional world or graph
documentation, but inspection does not confer authority. Full graph/world
access should remain an admin/development, offline-analysis, or explicitly
disclosed capability rather than an ordinary player-client assumption.

## Decision checkpoint

| Candidate representation | What is authoritative/persisted | Client/parser burden | Degradation and consistency | Coverage / unresolved contract |
| --- | --- | --- | --- | --- |
| **A. Authoritative text plus annotation spans** (`text`, `start`, `end`, `tokens`), used by this diagnostic | Text once, plus offsets and advisory tokens | Clients slice one text value using the agreed offset unit; adapters need no author-markup parser | Plain clients read `text`; unknown tokens leave the selected substring unstyled; flat ordered spans are easy to validate | Covers inline annotation on named eligible fields. Offset unit is unresolved across languages. |
| **B. Authoritative runs with plain text derived** | Ordered run text and tokens only | Every client concatenates runs for search, copy, accessibility, and fallback | No duplicate text authority, but whole-text operations allocate/derive a second view; run-boundary whitespace must remain exact | Avoids cross-language numeric offsets; nested/overlapping semantics require a tree or remain forbidden. |
| **C. Duplicated `plain_text` plus textual runs** (the first diagnostic version) | Both the full text and every run's text | Simple reads, but every producer and validator must enforce `plain_text == concat(runs)` | Best immediate fallback but two mutable text authorities can diverge; a required consistency invariant only detects the duplication | Rejected as the default recommendation unless a measured client need justifies duplicate storage. |
| One bounded inline markup string | Source or evaluated markup string | One shared parser before adapters; unsupported clients otherwise expose syntax | Requires parser-derived plain text to avoid leaking markup | Defines author syntax, not the neutral client representation. |
| Existing fragment/group `PresentationHints` | Whole-fragment semantic/advisory tokens | Low; adapters map known tokens | Existing readable content remains complete | Keep for whole-object meaning; cannot represent a partial inline span. |
| Parallel HTML/ANSI payload | Duplicate source plus adapter output | High and renderer-specific | Easy to diverge or lose fallback | Reject: it makes realization canonical and creates two text authorities. |

The executable comparison currently realizes candidate A. Offsets are **Unicode
scalar-value indices**: the parser rejects surrogate code points, and Python's
string indices then count the intended unit. JavaScript string indexing counts
UTF-16 code units, so an astral character before a span produces a different
numeric offset. A JavaScript client could iterate code points (`Array.from`) or
the wire contract could instead choose UTF-16 units, UTF-8 byte offsets, or
candidate B. The experiment intentionally does not choose among them.

The boundary that survives the comparison is smaller than a schema decision:
keep whole-fragment and group meaning in `PresentationHints`; parse author
syntax once before adapters; carry one neutral attributed-text value only on
explicitly eligible fields; let adapters map tokens locally. Selecting A versus
B, the offset unit, the exact discriminated schema, and persistence behavior is
the design stop requested by #454, so no production type or REST/CLI/Web path
is changed here.

## Observed current gaps

- REST's `html` profile still recursively transforms dictionary keys named
  `text` or `content`; the diagnostic proves an arbitrary nested lookalike must
  remain untouched.
- Web currently assumes ordinary string content and builds classes directly
  from `style_tags`; production needs deterministic collision-safe token
  normalization. The diagnostic hex-encodes every UTF-8 byte, including empty,
  underscore, punctuation, and Unicode inputs, rather than using an ambiguous
  escape-looking substring.
- Rich currently renders Markdown for `content_format="md"`, but does not
  consume a neutral inline-span value or public world style bindings.
- The current recursive Jinja session strips each render result. This revision
  evaluates the whole literal markup value before parsing spans, avoiding the
  first experiment's run-boundary whitespace loss.
- Plain content, identity, order, provenance, choices, media fallback, groups,
  and UX event placement can already survive without theme data. Styling and
  theme selection remain adapter-local and advisory.
