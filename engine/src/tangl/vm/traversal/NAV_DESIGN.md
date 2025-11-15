## Navigation vs Automatic Redirects

StoryTangl distinguishes between two types of edge traversal:

### User Choices (Manual Navigation)
- Edges with `trigger_phase=None` (the default)
- Always require explicit user selection via `Frame.resolve_choice()`
- **Never auto-followed**, even if there's only one available choice
- Use case: Player decisions, "Continue" prompts, branching paths

### Automatic Redirects (Triggered Jumps)  
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

### Navigation Assistant Pattern

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