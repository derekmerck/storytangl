World Designs
=============

Prospective stories, demonstration plans, and expansions of existing worlds.
These documents preserve the reader's intended experience, the StoryTangl
capabilities it would exercise, and a first playable proof. Inclusion does not
mean that a world or its proposed engine features have shipped or been scheduled.

The executable `world catalog <https://github.com/derekmerck/storytangl/blob/main/worlds/README.md>`_
describes the teaching collection that exists. This collection describes possible
next uses. The `showcase portfolio (#395) <https://github.com/derekmerck/storytangl/issues/395>`_
tracks implementation work; individual issues retain dependencies, acceptance
criteria, and live execution status.

The collection
--------------

.. list-table:: Developed briefs
   :header-rows: 1
   :widths: 20 40 40

   * - Brief
     - Experience to preserve
     - Capability pressure
   * - :doc:`salon-season`
     - The same social history acquires different meanings under successive regimes.
     - Favor readouts, assembled evidence, institutional judgment, and later testimony.
   * - :doc:`patient-zero`
     - Recovering a companion's capabilities restores their ability to refuse.
     - One persistent person shared by configuration, resources, willingness, and narration.

:doc:`concept-seeds` collects Constraint-Collapse Mystery, Two Readers, One Graph,
Automata Chop-Shop, Second Bell, and a Fogbound Manifest showcase.
:doc:`world-expansions` records possible extensions to Coronate the Regent,
Marmoset Island, the Grand Grotto companion story, and Hungry Colony. Existing
worlds remain playable independently of these proposals.

.. toctree::
   :maxdepth: 1

   salon-season
   patient-zero
   concept-seeds
   world-expansions

Choosing the next experiment
-----------------------------

The smallest content-led candidate is a Coronate connective scene and ending
callback: its mechanical skeleton already exists. Marmoset Island can likewise
test social continuity while reusing its current contest and presentation paths.
Automata Chop-Shop and Patient Zero ask the stronger composition question: do
several mechanics actually agree on one durable individual? Two Readers and the
Constraint-Collapse Mystery carry larger open channel/coordination and runtime
constraint questions. Their story value does not make those contracts implemented
or make them the cheapest next demo. These are selection considerations, not an
execution order or a replacement for the linked issues.

How to develop a design
-----------------------

Start with the premise and experiential invariant, then map features to the
experience. Quiet scenes, humor, description, and aftermath do not need to
justify themselves by introducing a mechanic. A story can primarily exercise
already landed capabilities.

Use a small common record, expanded only as the concept develops:

* **Premise and experiential invariant:** what happens, and what must remain
  interesting or recognizable to the reader.
* **StoryTangl connection:** existing rails, proposed compositions, and genuinely
  missing platform work. Keep these three claims distinct.
* **Unresolved questions:** story decisions and technical uncertainty. World-owned
  policy is a valid answer; not every question calls for a framework.
* **First playable proof:** a bounded situation and observable consequences that
  would test the idea. It remains an experiment proposal until work is committed.
* **Pointers:** source/inspiration, related issues, and any executable world or
  maintained witness. Preserve provenance when extracting a brief from an issue.

Ordinary descriptions such as ``concept seed`` and ``developed brief`` express
editorial maturity, not another schema or status dashboard. Tutorial, fixture,
conformance world, and showcase describe different purposes. Reuse the substantial
exemplar decomposition in :doc:`../design/story/MECHANICS_FAMILIES`: pressure
structure, deliberate approximation, bespoke residual/framework friction, and
mechanical, narrative, and client evidence.

Plan and ownership
------------------

This documentation pass moves Salon Season, extracts Patient Zero's durable story
design, and collects smaller seeds and expansion directions from the portfolio.
It starts no story implementation and changes no engine contract. Approved design
checkpoints are not proof that their proposed APIs or compositions have shipped.
Capability assessments are an orientation snapshot checked on 2026-10-28; refresh
source, tests, and issues before choosing an implementation slice.

Develop small seeds here before splitting out files or issues. Give a longer
brief space when its characters, pressure, and vertical need development. Issues
own actionable decomposition and live progress. Extracting narrative intent does
not close unfinished or parked issues or put an experiment on the critical path.

When a concept is selected for implementation, open or designate an issue for its
first bounded playable proof; do not create implementation issues merely because
a concept enters this catalog.

When a bounded world is ready for ``worlds/``:

* Supply a stated purpose, runnable bundle, honest README, and maintained witness
  through a supported client or Service surface. Claim only what is exercised;
  no all-client or complete-campaign requirement is implied.
* Preserve focused fixtures. Build a sibling when expansion obscures a narrow
  proof. Reuse shared mechanics rather than another world's private domain package.
* Let its README own implemented behavior and running instructions. Promote the
  developed intent to an adjacent design note when useful; leave a summary and
  link here instead of maintaining two specifications. Preserve a pointer for
  an existing published document location when it moves.
* Add intent and a concise demonstrated capability (or optional representative
  image) to ``worlds/README.md`` in the same change. Catalog automation remains
  `#461 <https://github.com/derekmerck/storytangl/issues/461>`_; conformance evidence
  remains `#438 <https://github.com/derekmerck/storytangl/issues/438>`_.
* Mark unimplemented expansions explicitly. External consumer worlds may stay in
  their own repositories; a design link does not require copying their content
  or assets into this teaching collection.

A brief authorizes no general story, companion, pacing, or solver framework.
Its first proof should reveal whether existing composition is enough and which
repeated, engine-general gap actually remains.
