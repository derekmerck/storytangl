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
