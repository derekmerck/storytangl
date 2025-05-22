from enum import Enum

class ResolutionState(Enum):
    UNRESOLVED = "unresolved"  # indeterminate, no provider discovered
    RESOLVED = "resolved"      # requirement is satisfied, ungated provider assigned
    UNRESOLVABLE = "unresolvable"    # requirement cannot be met within constraints
    IN_PROGRESS = "in_progress"      # currently searching for a resolution

    # todo: These are valid states, maybe gated doesn't need a status flag, it just is a test given a context
    UNRESOLVED_AND_GATED = "unresolved_and_gated"
    RESOLVED_BUT_GATED = "resolved_but_gated"  # requirement is satisfied, but is currently gated and unavailable
