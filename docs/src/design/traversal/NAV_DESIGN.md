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

That makes the dispatch layer a statement about **whose concern preempts whose**.

**Application-wide — preemptive, indifferent to local state.** *"You have seen all the
content; here is how to subscribe for updates."* It does not matter where the player was
going; they are going to the outro. The condition is orthogonal to the fiction and
dominates it.

**World — conditional, and abstains when its condition does not hold.** *"The bridge
collapses under your weight and you tumble into the abyss"* when the crossing
prerequisites were not met. If they were met, the handler returns `None` and the player
takes the regular crossing. The redirect is a legitimate alternate destination, not a
failure — that is what distinguishes it from `validate_edge`, which folds with `all_true`
and **blocks** the move rather than substituting a different one.

### The layer that actually preempts is `GLOBAL`, not `APPLICATION`

The declarative surface above — edges carrying `trigger_phase` — is itself implemented as
a handler: `follow_triggered_prereqs` / `follow_triggered_postreqs` in
`vm/system_handlers.py`, registered through `@on_prereqs` into `vm_dispatch`, whose
`default_dispatch_layer` is **`SYSTEM`**. Since `SYSTEM` (1) sorts before `APPLICATION`
(2), and interception gives the decision to whoever gets there first:

| Order | Handler | Claims when |
|---|---|---|
| `GLOBAL` (0) | *(nothing registered today)* | — |
| `SYSTEM` (1) | `follow_triggered_prereqs` | **any** authored `trigger_phase` edge whose guard passes |
| `APPLICATION` (2) | app-wide redirects | only if no trigger edge fired |
| `AUTHOR` (3)+ | world/world-instance handlers | only if nothing above claimed |

So an app-wide outro registered at `DispatchLayer.APPLICATION` is **preempted by any
authored trigger edge** — the bridge would win over the outro, which inverts the intent.
A redirect that must genuinely trump story-level ones has to register at
`DispatchLayer.GLOBAL`, the only band below `SYSTEM`.

This is the layer-name trap again: "application-wide" describes *reach*, and the layer
named `APPLICATION` does not deliver it here because the declarative trigger-edge scanner
sits below it. Worlds that express their redirects as `trigger_phase` edges (the normal
path) are effectively redirecting at `SYSTEM`.
