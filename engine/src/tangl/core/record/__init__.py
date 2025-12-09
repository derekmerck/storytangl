# language=rst
"""
Records & Streams
=================

Overview
--------

The records/streams layer captures **runtime history** in a way that is:

* **Frozen** – records are immutable snapshots once created.
* **Sequenced** – each record has a monotone sequence number within a stream.
* **Graph-independent** – records do not require graph membership; they can be
  persisted, replayed, or shipped across process boundaries.
* **Identifiable** – every record has a stable UUID and a lightweight origin
  pointer back to the thing that caused it to exist.

Concretely, this layer provides:

* :class:`Record` – the common base for all streamable runtime artifacts.
* :class:`StreamRegistry` – an append-only, sequenced collection of records.
* A small set of **role-specific** record subclasses that cover the main
  runtime concerns of the engine.

Core concepts
-------------

Record
~~~~~~

A :class:`Record` is the smallest unit of runtime history.

It is a frozen, graph-independent entity with:

* ``id: UUID`` – unique identity.
* ``seq: int`` – a monotone sequence number **over all records**.
* ``origin_id: UUID | None`` – the entity primarily responsible for this
  record being created (behavior, node, service, etc.).
* ``tags: set[str]`` – arbitrary labels for downstream indexing, filtering,
  and multiplexing.
* An arbitrary payload defined by subclasses.

Records do **not** model game/world state directly.  Instead, they describe:

* What happened (:class:`CallReceipt`).
* What the world looked like (:class:`Snapshot`).
* What was shown to the player or client (:class:`BaseFragment` subclasses).

Records are immutable.  Any “update” is represented by appending a **new**
record with a higher sequence number.

Record roles
~~~~~~~~~~~~

Rather than a single monolithic record type with many optional fields, core
defines a small set of **role-specific** record subclasses:

1. **Compute records** (:class:`CallReceipt`)

   * Capture the outcome of a behavior or handler call.
   * Typically include ``result``, ``result_type``, and a ``result_code``
     that summarizes success/failure semantics.
   * ``origin_id`` normally points at the behavior or handler that ran.

2. **State records** (:class:`Snapshot[T]`)

   * Capture a (deep) copy of an entity or graph at a point in time.
   * Used for persistence, time-travel, and debugging.
   * Often content-addressable via a ``content_hash`` so that identical
     snapshots can be deduplicated.

   Higher layers may introduce **state-adjacent** artifacts that follow the
   same conventions but live outside the stream:

   * A *Template* class in the script manager, used to instantiate new
     entities into the graph (a structured “pre-state” that has not yet
     been realized).
   * A *Patch* record in the VM, representing a single update or delta used
     to rebuild state from snapshots (event-sourced replay).

   These are not defined in core, but they are intended to be understood as
   variants on the same “state record” idea: full-copy (:class:`Snapshot`),
   pre-state (Template), and delta-state (Patch).

3. **Narrative/UI records** (:class:`BaseFragment` and subclasses)

   * Capture content destined for the player or a client UI.
   * Examples: text fragments, media fragments, choice prompts, layout hints.
   * These are the only record types that are expected to cross the
     Python/JSON boundary regularly.

The goal is that a downstream reader can make a **cheap, structural decision**
based on the concrete subclass:

* “This is a :class:`CallReceipt` → it tells me how a behavior ran.”
* “This is a :class:`Snapshot` → it tells me what the world looked like.”
* “This is a :class:`Fragment` → it tells me what to render.”

Type vs channel vs tags
-----------------------

Python type and ``is_instance`` matching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within the engine, the **preferred** way to distinguish record roles is by
their concrete Python type.

The registries expose this via criteria such as:

* ``stream.find_all(is_instance=CallReceipt, ...)``
* ``stream.find_all(is_instance=Snapshot, ...)``
* ``stream.find_all(is_instance=BaseFragment, ...)``

Under the hood, the ``is_instance`` criterion is implemented in using
``isinstance(record, <class>)``, and is combined with any other match
criteria (tags, channels, seq ranges, etc.).

This is the canonical way to answer questions like:

* “Give me all fragments in this section.”
* “Give me all snapshots after seq N.”
* “Give me all call receipts for this behavior.”

Record subclasses should prefer explicit Python types and well-documented
payload fields instead of inventing additional string-type discriminators.

Fragment types & presentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At the **presentation boundary**, clients do *not* see Python types – they see
JSON.

For narrative/UI records, subclasses typically provide a **fragment type**
field (for example, ``fragment_type: Literal["text", "media", ...]``) and
additional fields such as:

* For media fragments: ``content_type`` (``"image"``/``"audio"``/``"video"``),
  and ``content_fmt`` (``"url"``/``"base64"``/``"svg"``), etc.

These fragment-level type hints are intended for **clients**, not for
in-engine routing:

* The VM/service layers operate on concrete Python classes and
  ``is_instance`` matching.
* Serialized responses expose fragment type information so that a browser,
  CLI, or other consumer can decide “how do I render this thing?”

Channels via tags
~~~~~~~~~~~~~~~~~

A :class:`StreamRegistry` holds **many** different record types in one log.
For example, a single stream might interleave:

* Call receipts from VM dispatch.
* Snapshots of the ledger or graph.
* Journal fragments for the player.

To handle this multiplexing cleanly, we use **tags** rather than a dedicated
``channel`` field.  The conventions are:

* Tags are free-form strings.
* A *channel* is a tag of the form ``"channel:<name>"``.
* Helpers such as ``has_channel("journal")`` are provided to check for
  ``"channel:journal"`` in the tag set.

Find queries can combine type and channel, for example:

* ``stream.find_all(is_instance=BaseFragment, has_channel="journal")``
* ``stream.find_all(is_instance=CallReceipt, has_channel="planning")``

Recommended usage:

* Use **``is_instance=...``** to distinguish **what kind** of record you are
  looking at (compute / state / narrative / domain-specific subtype).
* Use **channels** (encoded as tags) to distinguish **where** records came
  from or how they are grouped:
  * Journal vs diagnostics vs stack vs domain-specific streams.
  * Multiple journals or perspectives sharing the same fragment types.
* Use **additional tags** for cross-cutting concerns (e.g. debugging, test
  markers, feature flags).

In other words:

*“Role by type; source by channel; cross-cutting concerns by tags.”*

StreamRegistry
--------------

A :class:`StreamRegistry` is an append-only, sequenced collection of records.

Key properties:

* **Append-only** – records are only added; they are not mutated in-place.
* **Sequenced** – each appended record is assigned a strictly increasing
  ``seq`` within that stream.
* **Heterogeneous** – any :class:`Record` subclass can be stored in the same
  stream.
* **Queryable** – records can be filtered with common helpers for type, seq range, tags, and channel, as well as with arbitrary criteria by using a predicate function.

Typical operations include:

* ``append(record)`` – assign the next ``seq`` and store the record.
* ``last()`` – retrieve the latest record (by seq).
* ``get_slice(start_seq, end_seq)`` – retrieve a range of records.
* Marker/section helpers (e.g. “get all records between two logical
  markers of a given type”).

Invariants
~~~~~~~~~~

For each :class:`StreamRegistry` instance:

* ``seq`` is monotone increasing; no two records share a seq.
* Once appended, a record is immutable.  Any “change” is modeled as a new
  record with a higher sequence number.
* The registry does not itself interpret the payload; it only enforces
  sequencing and basic filtering.  Higher-level conventions (for example,
  “what is a journal entry?”) live in the VM/service/story layers.

Motivation & design intent
--------------------------

The records/streams layer exists to decouple **runtime history** from
**live world state** and from any particular persistence or presentation
strategy.

* Records are small, frozen, self-contained facts.
* Streams are simple, ordered logs of those facts.
* Everything else (journal rendering, undo/redo, persistence, analytics)
  builds on top of this minimal foundation.

By specializing a few core record roles (compute/state/narrative) and
standardizing on ``origin_id`` + tags/channels, we keep the engine free to
add new record subclasses **without** needing to invent new infrastructure:

* New record types just subclass :class:`Record`, choose a role, and define
  their payload.
* Higher layers can introduce related concepts (Templates, Patches, richer
  fragment types) that follow the same conventions.
* Existing tools (serialization, streaming, filtering, time travel) continue
  to work as-is.

"""
from .record import Record
from .snapshot import Snapshot
from .base_fragment import BaseFragment
from .stream_registry import StreamRegistry
