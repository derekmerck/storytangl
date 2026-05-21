# Simulation Mechanics

`tangl.mechanics.simulation` contains small operational-simulation kernels that
attach to ordinary StoryTangl runtime seams. The first member is a deterministic
queueing proof: future events are pending work in a mutable core `Registry`,
state changes happen through the existing game UPDATE phase, and observations
are emitted as normal journal fragments.

The package deliberately does not replace sandbox scheduling. Sandbox schedules
describe availability against a derived `WorldTime`; the simulation event
calendar stores exact future events and supports next-event advancement. Both
share normalized integer time and can be bridged later when a sandbox scope wants
to host a queueing or resource simulation as a tick-compatible observer.

Future work should explore a shared timed-process/counter vocabulary under both
`ChargeFacet` and queue service completions. The queueing demo should keep using
calendar-scheduled `service_complete` events for now; lamp charge should keep
using sandbox tick depletion. If another timer-like mechanic proves the same
shape, promote the common counter/progress/completion surface into a small
mechanics-level type and leave charge and queueing as domain-specific adapters.
