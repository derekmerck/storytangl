# Docstring & Autodoc Conventions

## Goals

**See also:** [Coding Style & Architecture](coding_style.md) — semantic guidelines for packages, modules, layers, and extension points.

- **Communicate intent, not internals** at the class level.
- Keep the **conceptual map** in the subpackage `__init__.py` (layers & design intent).
- Use module- and member-level docs for **details and usage**.
- Produce **stable diffs** (predictable section order, minimal churn).
- Render cleanly with Sphinx autodoc, with reliable cross-references.

---

## A. Class docstrings: "Why / Key Features / API (+ optional Notes / See also)"

These are the *canonical* documentation for single-purpose modules (like `Frame` or `Context`).  
They should always carry the full `Why / Key Features / API / Notes` structure.

Every *public* class gets a concise docstring with this exact section order:

1) **One-line signature title**  
   A single “constructor-ish” line just after the class name. Keep it short and informative; it’s documentation, not a type checker:
   ```
   ClassName(param1: Type, param2: Type)
   ```
   - Do not list default values or every field—keep ≤ ~80 chars. This is an orientation hint, not a type contract.
   - Prefer high-signal params (e.g., "graph: Graph, cursor_id: UUID").

2) **One-sentence summary** (optional)  
   A single sentence that names the concept in plain English.

3) **Why**  
   Explain the purpose: *what problem this class solves* and *why it exists in the architecture* (1–3 sentences).

4) **Key Features**  
   3–6 bullet points. Each bullet is a capability or behavior category—*not* an exhaustive method list. Use terse, parallel constructions:
   - Start bullets with **Bold Noun/Verb** if helpful (“**Typed** – …”, “**Auto-registration** – …”).
   - Mention only the most important methods *in context* with Sphinx roles where it clarifies.

5) **API**  
   A short, curated list of the 5–8 most important members. Use Sphinx roles (`:attr:`, `:meth:`, `:class:`, `:func:`), and if the same name appears in multiple places, use fully qualified paths. For readability in our style:
   - Show “paired” operations as `add/remove`, “finders” as `find_one/find_all`.
   - When linking, prefer short forms if the current module context resolves; otherwise fully qualify:
     - Short: `:meth:`find_all``  
     - Qualified: `:meth:`~tangl.core.registry.Registry.find_all``

6) **Notes** (optional)  
   Use for crisp distinctions or caveats users must know (“Journal vs Events”, “immutable sequence semantics”, etc.). Keep it brief.

7) **See also** (optional)  
   Short list of sibling concepts with cross-refs.

**Formatting rules**
- Section headers and underline characters are literal and fixed:
  - `Why` → `----`
  - `Key Features` → `------------`
  - `API` → `---`
  - `Notes` / `See also` → `-----`
- Keep bullets to one line if possible; wrap subsequent lines with 2-space hanging indent (Sphinx does this naturally).
- Voice: **present tense**, **active**, **no “we”**; address the class’s behavior, not the author.

**Example skeleton**
```rst
ClassName(param: Type)

One-line summary of what this is.

Why
----
What problem it solves and why it exists.

Key Features
------------
* **Typed** – …
* **Auto-registration** – …
* **Scoped search** – :meth:`find_one` / :meth:`find_all` within …

API
---
- :meth:`add` / :meth:`remove` – …
- :meth:`find_all` – …
- :attr:`label` – …

Notes
-----
One or two bullets of critical nuance.

See also
--------
:class:`SiblingClass`, :class:`~package.module.Other`
```

### Enums

Keep them compact: short summary + Why + 1–3 **Key Features** bullets + **API** if there are helper methods (e.g., ":meth:`apply_order`"). Do not list every member in prose; rely on autodoc member list.

### Record-like classes (immutable artifacts)

Follow the same template, but include a bullet under **Key Features** noting the fixed `record_type` (e.g., "`record_type='event'` for stream filtering").

---

## B. Subpackage `__init__.py` docstring: “Conceptual layers + Design intent”

Each subpackage’s top-level docstring introduces *conceptual layers*, then names the key classes under each layer, and closes with **Design intent**.

**Required sections**
- **Conceptual layers** (numbered): each layer name is a noun phrase; within each layer, list the most important classes and how they relate.
- **Design intent**: 1–3 sentences describing how this subpackage is meant to be used or extended, and (importantly) *what it intentionally does not decide*.

**Linking conventions**
- Use `:ref:` to link to labeled sections in the subpackage RST summary (e.g., `:ref:`core-identity``).
- Use `:class:` for API symbols; if ambiguous, qualify with `~tangl.core.X`.

**Example (we already follow this)**
- Layers: Identity & Collection, Topology, Runtime Artifacts, Dispatch, Capability.
- Intent: “isolates minimal abstractions… without presupposing narrative content.”

---

## C. Module-level docstrings

**Policy:** If a module exposes a single public class with a full class docstring, omit the module docstring or keep it to a 1–3 line summary. Use a full module overview only when it meaningfully introduces multiple peer classes as a cohesive concept.

Use **only when** you need to introduce a *new conceptual layer* or explain *why multiple classes belong together*.  
If the module contains a single major class (like `Frame`, `Context`, `Ledger`, etc.) and the class has a detailed docstring, the module docstring should be **very short** or omitted entirely. In any case, **do not repeat** the same in the module docstring.

When necessary, use module docstrings **sparingly** to answer one of:
- “What’s in this module and how it differs from siblings?”
- “What invariants or policies govern this module?”

Keep them short. Place long tutorials/usage in higher-level narrative docs, not module docstrings.

**Terse style:**
```rst
Execution context for one frame of resolution.
Thin wrapper around the graph, cursor, and scope providing deterministic RNG.
Used when the module contains one primary class with a full docstring.
```

→ Keep it to 1–3 lines: *“what this module provides”* and *“in what part of the architecture it’s used”*.

If a module contains **multiple peer classes** (e.g., several related planning/offer types), then the module docstring can instead have our usual `Why / Key Features / API` sections, introducing the shared design intent and linking to the contained classes.

### Heuristic

- **Single public class:** module docstring = *one-sentence summary or none*.  
- **Multiple related classes:** module docstring = *conceptual overview with Why/Key Features/API for the group*.  
- **Subpackage-level docstring** (in `__init__.py`): full conceptual map (always).

---

## D. Member docstrings (methods/attributes)

- Only document **non-obvious** or **externally important** methods and attributes.
- For trivial accessors, prefer the class-level “API” bullets over per-member docstrings.
- When documenting parameters, prefer the imperative one-liner over full numpydoc unless complexity justifies it.
- For Pydantic fields:
  - If a field is “public but doc-private,” mark it with `json_schema_extra={"doc_private": True}` and let our Sphinx `autodoc_skip_member` hook hide it in rendered docs.
  - Avoid polluting constructor signatures: if signatures are shown, we filter them (or we simply hide Pydantic signatures, per our conf).

---

## E. Cross-references & Sphinx roles (do this, not that)

- Use the standard roles:
  - `:class:`, `:meth:`, `:func:`, `:attr:`, `:mod:`, `:ref:`, `:deco:` (Sphinx decorator role).
  - Use `:attr:` for properties (Sphinx treats properties as attributes in xref roles).
  - For Python stdlib objects, prefer `:py:class:`collections.ChainMap`` (or plain code if resolution is flaky).
- When linking to *sections* in RST summaries, use labels and `:ref:` with or without custom text:
  - `:ref:`core-topology`` or `:ref:`Topology <core-topology>``.

---

## F. Autodoc RST “summary pages” (per subpackage)

Each subpackage summary RST mirrors **Conceptual layers**. For each layer:

- Add a label (e.g., `.. _core-topology:`).
- Provide a terse layer header (`Topology`).
- List classes with `.. autoclass:: package.Module.ClassName` in the same order as the conceptual docstring.
- Resist the urge to include every helper; keep these pages **curated**. (The full API exists in the HTML nav; this page is a guided map.)

**Example**
```rst
.. _core-artifacts:

Artifacts
---------
.. autoclass:: tangl.core.Record
.. autoclass:: tangl.core.StreamRegistry
.. autoclass:: tangl.core.Snapshot
.. autoclass:: tangl.core.BaseFragment
```

---

## G. Pydantic & signatures (house policy)

To avoid leaking internal/derived fields in constructor signatures:

- Prefer **hiding Pydantic signatures** globally (cleanest), *or* rewrite signatures with a filter that drops fields with `json_schema_extra={"doc_private": True}`.
- Always keep `uid` present in `unstructure`, but we do **not** list it as a constructor argument in docs.
- For structuring, **do not override** `Entity.structure()`; subclasses implement `_structure_post(original)` / `_unstructure_post(out)` hooks (factory pattern). Document these hooks in the class’s **API** bullets if they exist.

We maintain an autodoc skip hook to hide fields marked with `json_schema_extra={"doc_private": True}` from member tables; optionally filter constructor signatures the same way if you choose to display them.

---

## H. Naming, terms, and tone

- Use consistent terms across docs:
  - **Record** (immutable artifact), **Patch** (list[Event]), **Journal** (fragments), **Snapshot**, **Handler**, **JobReceipt**, **Domain**, **Scope**, **GraphItem/Node/Edge/Subgraph**, **Registry**, **Singleton**.
- Type adjectives: **Typed**, **Auto-registration**, **Scoped search**, **Integrity checks**, **Sequenced**, **Bookmarks**, **Channels**, **Prioritized**, **Selectable**, **Auditable**.
- Prefer **Node/Edge/Subgraph** over generic “vertex/edge” in our context, but “vertex” is acceptable in summaries as a synonym.
- Avoid implementation slang; keep it product-level.

- **Canonical capitalization**:
  - Phases are UPPERCASE (INIT, VALIDATE, PLANNING, PREREQS, UPDATE, JOURNAL, FINALIZE, POSTREQS).
  - Use “Journal” (fragments) vs “Events” (replayable ops) consistently.

---

## I. Documenting Dereferencing & Iterator Patterns

### When to add Notes about dereferencing

If a class stores `*_id` fields and provides resolution methods/properties, document the pattern in **Notes**:

**For GraphItems (implicit graph access)**:
```rst
Notes
-----
Endpoint properties (``source``, ``destination``) resolve via the owning
graph. Every access goes through ``self.graph.get()`` for watchability.
```

**For Records (explicit registry parameter)**:
```rst
Notes
-----
Records are graph-independent. Use ``.blame(registry)`` to dereference,
unlike :class:`GraphItem` properties which use implicit ``.graph`` access.
This asymmetry preserves record immutability and topology independence.
```

**For Collections (fresh iterators)**:
```rst
Notes
-----
Returns a fresh iterator. Materialize with ``list()`` if multiple
passes are needed. See :ref:`common-pitfalls-iterators` for examples.
```

### Linking to architecture docs

When documenting dereferencing patterns, link to the central explanation:

```rst
See also
--------
:ref:`dereferencing-patterns` in [Coding Style](coding_style.md#15-dereferencing--resolution-patterns)
```

### Example: Comprehensive Edge docstring

```rst
Edge(source: Node, destination: Node, edge_type: str)

Directed connection between two nodes in the same graph.

Why
----
Encodes structure and flow (parent→child, dependency, sequence). Stores
endpoint ids for serialization, with properties that resolve to live nodes.

Key Features
------------
* **Typed** – optional :attr:`edge_type`.
* **Endpoint conversion** – pre-init validator accepts ``source``/``destination``
  as :class:`GraphItem` and converts them to ids.
* **Live accessors** – :attr:`source` / :attr:`destination` resolve via graph.

API
---
- :attr:`source_id`, :attr:`destination_id` – UUIDs (nullable for dangling edges).
- :attr:`source` / :attr:`destination` – properties with validation on set.
- :meth:`__repr__` – compact label showing endpoints for debugging.

Notes
-----
Endpoint properties resolve via ``self.graph.get()`` on every access,
enabling :class:`WatchedRegistry` interception. Mutation of endpoints
is allowed but updates only the ``*_id`` fields.

See also
--------
:class:`~tangl.core.graph.AnonymousEdge`,
:ref:`dereferencing-patterns` in [Coding Style](coding_style.md)
```

---

## J. Documenting Iterator Semantics

### When queries return iterators

Any method/property returning `Iterator[T]` should note the single-use nature:

**Minimal note (for obvious cases)**:
```rst
API
---
- :meth:`find_all` – yield entities matching criteria (fresh iterator).
```

**Explicit note (when it might surprise)**:
```rst
API
---
- :attr:`members` – yield members as `Iterator[GraphItem]`.

Notes
-----
Returns a fresh iterator on each access. Materialize with ``list(members)``
if multiple passes are needed. See :ref:`common-pitfalls-iterators`.
```

### Type hints in signatures

Document that we prefer `Iterator[T]` over `Iterable[T]`:

```rst
Notes
-----
Type hint ``Iterator[T]`` signals single-use. If materializing, use
``list()`` or ``tuple()`` explicitly rather than assuming reusability.
```

---

## K. Common Cross-References

Use these standard link targets in **See also** sections:

- `:ref:`dereferencing-patterns`` → [Coding Style § 15](coding_style.md#15-dereferencing--resolution-patterns)
- `:ref:`common-pitfalls-iterators`` → [Common Pitfalls](common_pitfalls.md#iterator-exhaustion)
- `:ref:`audit-tracking`` → [Coding Style § 12](coding_style.md#12-observability)
- `:ref:`priority-ordering`` → [Coding Style § 6](coding_style.md#6-handlers--dispatch)

---

## L. Documenting `is_dirty` and Audit Flags

If a class uses `is_dirty` or similar audit markers:

**In Entity docstring**:
```rst
Key Features
------------
* **Audit tracking** – :attr:`is_dirty` flags non-reproducible mutations
  for replay validation.

API
---
- :attr:`is_dirty` – read-only flag indicating tainted state.
- :meth:`mark_dirty` – mark entity as modified by non-reproducible means.
```

**In Registry docstring**:
```rst
API
---
- :meth:`any_dirty` – check if any entity in registry is marked dirty.
- :meth:`find_dirty` – yield all entities with ``is_dirty=True``.
```

---

## M. Examples & admonitions

- Place *short* examples inline (≤5 lines). Longer examples go in narrative docs.
- Use Sphinx admonitions **sparingly**:
  - `.. note::` for portability caveats.
  - `.. warning::` for behavioral footguns (e.g., mutability).
- In class docstrings, keep admonitions minimal (we used one in `Handler` for reserved kwargs—good).

---

## N. Privacy & surface curation

- Use `__all__` in `__init__.py` to curate public surfaces.
- For fields that are technically public but should be hidden:
  - Set `json_schema_extra={"doc_private": True}` on the field.
  - Our `autodoc_skip_member` hook will skip them in member tables.
  - Optionally strip them from constructor signatures via the signature filter (or hide signatures entirely).
- Avoid documenting internal cache/proxy attributes; expose behavior via methods in the **API** bullets.

---

## O. Checklists (for PRs)

**For a new class**
- [ ] Docstring includes: one-line signature, (optional) summary, **Why**, **Key Features**, **API**, (optional) **Notes/See also** in that order.
- [ ] “Key Features” has 3–6 bullets; “API” has 5–8 bullets max.
- [ ] Cross-refs resolve (`nitpicky = True` in `conf.py` helpful).
- [ ] Fields marked `doc_private` if they shouldn’t appear.
- [ ] If the class structures/unstructures children, it uses `*_post` hooks and mentions them in **API**.

**For a subpackage**
- [ ] `__init__.py` docstring has “Conceptual layers” + “Design intent”.
- [ ] Summary RST mirrors layers with `.. autoclass::` entries in the same order.
- [ ] Labels (`.. _core-…:`) exist and are used via `:ref:` in text.

**For a module**
- [ ] Module docstring explains the *difference* vs siblings or states module-specific invariants.
- [ ] Leave heavy usage to higher-level docs unless the module is standalone.
- [ ] If the module has a single public class with a full docstring, the module docstring is omitted or a 1–3 line summary.

---

## P. Sphinx config nudges

In `conf.py`, we (recommend):
```python
extensions += [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",          # if you want Google/Numpy style in rare cases
    "sphinx.ext.autosectionlabel",  # easy section links
]
autosectionlabel_prefix_document = True
nitpicky = True                     # catch unresolved refs early
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": False,
}
# Optional: hide pydantic model signatures globally (cleanest)
# extensions += ["autodoc_pydantic"]
# autodoc_pydantic_model_signature = False
```

---

## Q. Quick examples from our codebase (as reference)

- **Entity / Registry / Graph / Node / Edge / Subgraph / Record / StreamRegistry / Snapshot / BaseFragment / Handler / DispatchRegistry / JobReceipt / Singleton / InheritingSingleton / SingletonNode** all follow the template above.
- **Subpackage `tangl.core.__init__`** shows “Conceptual layers” and “Design intent”—copy that pattern for other subpackages (`tangl.lang`, `tangl.resolution`, etc.).
- **Subpackage summary RST** (`tangl.core.rst`) mirrors those layers with labeled sections and `.. autoclass::` lists—treat it as the canonical *map*.

---

## R. Related Guides

- [Coding Style & Architecture](coding_style.md) — layering, patterns, anti-patterns
- [Common Pitfalls](common_pitfalls.md) — iterator exhaustion, dereferencing traps
- [Planning Phase Roadmap](planning_phase_roadmap.md) — VM phase execution contracts
