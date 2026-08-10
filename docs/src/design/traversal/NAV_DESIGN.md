# Navigation vs Automatic Redirects

StoryTangl distinguishes between two types of edge traversal:

## User Choices (Manual Navigation)
- Edges with `trigger_phase=None` (the default)
- Always require explicit user selection via `Frame.resolve_choice()`
- **Never auto-followed**, even if there's only one available choice
- Use case: Player decisions, "Continue" prompts, branching paths

## Automatic Redirects (Triggered Jumps)  
- Edges with `trigger_phase=P.PREREQS` or `trigger_phase=P.POSTREQS`
- Auto-followed during phase execution when conditions are met
- No user interaction - transparent navigation
- Use case: Scene entry/exit, forced story beats, structural traversal

### Example: Single Choice Still Prompts
```python
# This creates ONE choice but user must still click it:
ChoiceEdge(
    source=block_a, 
    destination=block_b,
    label="Continue"  # No trigger_phase
)

# This would auto-advance with no prompt:
ChoiceEdge(
    source=block_a,
    destination=block_b, 
    trigger_phase=P.POSTREQS  # Automatic
)
```

## Navigation Assistant Pattern

Authors wanting "auto-continue on single choice" can implement this 
as an optional behavior at the application layer:
```python
def navigation_assistant(frame: Frame) -> ChoiceEdge | None:
    """Optional: auto-select if only one choice."""
    choices = list(frame.get_available_choices())
    if len(choices) == 1:
        return choices[0]
    return None
```
(redirect-precedence)=
## Redirect precedence: who claims the jump

Both phases fold with `first_result` (see *Layers order; registries scope; folds decide*
in the [glossary](../glossary.md)). Redirects **intercept**: the first handler to return
an edge claims the traversal, and nothing downstream can un-claim it. A handler with no
opinion must return `None`.

That makes the dispatch layer a statement about **whose concern preempts whose**. The
registry containing the handler independently determines where that concern is visible.

**Hard interception — explicitly `GLOBAL`.** *"You have seen all the content; here is how
to subscribe for updates."* If it must dominate even VM trigger handling, its handler
opts into `GLOBAL`. Register it in an application registry for application-wide reach or
in a world registry for the same precedence within that world only.

**World — conditional, and abstains when its condition does not hold.** *"The bridge
collapses under your weight and you tumble into the abyss"* when the crossing
prerequisites were not met. If they were met, the handler returns `None` and the player
takes the regular crossing. The redirect is a legitimate alternate destination, not a
failure — that is what distinguishes it from `validate_edge`, which folds with `all_true`
and **blocks** the move rather than substituting a different one.

### VM trigger scanning is a `SYSTEM` concern

The declarative surface above — edges carrying `trigger_phase` — is itself implemented as
a handler: `follow_triggered_prereqs` / `follow_triggered_postreqs` in
`vm/system_handlers.py`, registered through `@on_prereqs` into `vm_dispatch`, whose
`default_dispatch_layer` is **`SYSTEM`**. Since `SYSTEM` (1) sorts before `APPLICATION`
(2), and interception gives the decision to whoever gets there first:

| Order | Handler | Claims when |
|---|---|---|
| `GLOBAL` (0) | explicit hard intercepts | whenever their own condition and registry reach apply |
| `SYSTEM` (1) | `follow_triggered_prereqs` | **any** authored `trigger_phase` edge whose guard passes |
| `APPLICATION` (2) | ordinary application handlers | only if nothing above claimed |
| `AUTHOR` (3)+ | ordinary world and instance handlers | only if nothing above claimed |

An outro registered at `APPLICATION` is therefore preempted by a matching declarative
trigger edge. That is intentional: broad registry reach does not imply hard precedence.
A redirect that must dominate the trigger scanner explicitly selects `GLOBAL`.

The edge itself remains authored content; interpreting its `trigger_phase` is the VM's
`SYSTEM` behavior. Conversely, a world-owned handler may select `SYSTEM` or `GLOBAL` for
exceptional precedence and remains world-private because its registry, not its layer,
controls reach.
