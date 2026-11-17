# Night Shift — deterministic ED queueing

**World ID:** `ed_queue_demo` · **Role:** focused mechanics/teaching demo

Four patients arrive at a small emergency department. Each passes through
triage, imaging, and disposition, with one service slot at each station.
The queue, wait times, and final bottleneck result from processing scheduled
events, not from branching passages for each patient's journey.

## What it demonstrates today

- `EdQueueSimulation` configures arrivals at turns 0, 2, 4, and 8.
  Triage takes 3 turns, imaging 5, and disposition 2; every station has
  capacity one.
- The shared simulation kernel uses a deterministic future-event list.
  An arrival or service completion updates patients and station state
  and can schedule subsequent events. The player **does not** choose each
  patient's next action.
- In the simulation block, the reader can choose **Run next event** or
  **Run until complete**. Advancing time is **explicit**: events do not
  progress in real-world time while the client waits for input.
- The resulting event trace is rendered through ordinary StoryTangl JOURNAL
  fragments. The kernel supports log or narrative text projections from
  the same trace; the shipped demo uses the log default.
- On completion the story advances to its summary. The maintained tests
  expect four completed patients, final turn 25, mean length of stay 14.0,
  and **imaging** as the bottleneck.

The world is declared in [`script.yaml`](script.yaml) and
[`world.yaml`](world.yaml), with a small configuration in
[`ed_queue_demo/domain.py`](ed_queue_demo/domain.py). The general
future-event calendar and queueing rules live in
[`tangl.mechanics.simulation`](../../engine/src/tangl/mechanics/simulation/README.md).
The executable loading and event-order witnesses are in
[`test_ed_queue_demo_world.py`](../../engine/tests/loaders/test_ed_queue_demo_world.py)
and [`test_queueing.py`](../../engine/tests/mechanics/simulation/test_queueing.py).

Run it with the usual StoryTangl client by selecting the world
`ed_queue_demo`, or run those focused tests to verify its mechanics.

## Relationship to The Unobserved Day

The proposed
[**Unobserved Day**](../../docs/src/world-designs/concept-seeds.md#the-unobserved-day-autonomous-incidents)
is deliberately **related but distinct**. Night Shift proves that several
entities can undergo deterministic causal changes without separate reader
choices for each event. It does **not** yet prove that a reader can shift
observational focus without advancing time, intervene in the queue, and
observe offscreen consequences; nor does it model characters' independent
knowledge or conversations.

A **small first extension of Night Shift** could introduce a read-only
observer focus, one legal intervention (for example, delaying a service
start), and later time advancement. Compare a baseline run, a run with
observation-only focus changes, and a run with an intervention:

- **Observation-only:** the underlying event trace is unchanged, even
  though the visible reports may differ with observer focus.
- **Intervention:** downstream events can change, including at an
  unobserved station; the change is recorded through ordinary
  simulation/JOURNAL behavior.

**The distinct narrative proof** in Unobserved Day then adds independently
scheduled characters, character-specific knowledge propagation, and later
actions that depend on events the player never witnessed. It should reuse
the event/scheduling and presentation primitives where appropriate, not
create another event engine solely to obtain the same causal behavior.

Neither proposed experiment is implemented here, and neither requires
the simulation to run asynchronously while the player is idle. Moreover,
moving the ordinary StoryTangl traversal cursor is not automatically a
read-only operation: an observational UI must avoid unintentionally
running traversal side effects.
