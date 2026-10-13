# Optional prose extensions

Status: explicit concept naming/reference slice (#534 slice 1) implemented;
exact lexical name/nominal/#intro linking remains deferred.

Rendering sessions and dialog micro-blocks are existing realization helpers.
`naming` is an optional Story extension adopted by world domains before
compilation through their existing class registry and authority chain. Story
does not import this module to activate it. It installs no alternate registry
or fragment hierarchy; its behaviors use normal Story/VM dispatch tasks.

`ConceptReference` is a small value describing a namespace referent, wording
intent, and introduction. `ProseSegment` pins order across body references and
speaker displays. These contain no live graph pointers; normal typed model
fields and constructor-form graph persistence suffice. Concepts store proper
and anonymous wording. Knowledge belongs to the current provider and narrator.

`NamingOperations.reference` is pure and uses existing named-text-aspect
dispatch; `introduce` writes concept-local knowledge in UPDATE/FINALIZE effects
or explicit committed JOURNAL realization. Explicit
Python Jinja templates invoke the same operations once. Display labels prohibit
introductions. Per-concept override/opt-out precedes the nearest world-supplied
kind default; absent policy means off. Literal text and graph identity are stable.

Successful save/restore, patch replay, and explicit rollback are the durability
contract. Unexpected exceptions propagate under existing non-atomic traversal
semantics; the #534 scope decision excludes general failure recovery. The
compiled-world FINALIZE probe and implications are recorded in
`docs/src/design/story/CONCEPT_LINKED_PROSE.md`.

The downstream witness is `worlds/concept_naming_demo`, exercised by
`engine/tests/prose/test_naming.py`, including JSON-backed ServiceManager flow.
Reopening a JSON manager in the same process retains live World/type/authority
registration. The true subprocess witness calls normal `open_world()` bootstrap
before opening the saved session. Soft reset/hot reload is separate work.

Ordinary raw/Jinja dialog currently renders the entire block before composition
parses and binds speakers. Mid-utterance introduction therefore leaves no
pre-body knowledge available at label-binding time. Ordered ProseSegment
templates already bind labels before evaluating their bodies once; extending
that guarantee to the ordinary pipeline is an unresolved realization-ordering
checkpoint, not permission to derive earlier labels from end-of-batch knowledge.
Attributed dialog tone/avatar and presentation-class work remains #454/#457.
