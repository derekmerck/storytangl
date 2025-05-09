from tangl33.core import Node, Edge

class StoryNode(Node):
    """A traversable narrative node in the story."""
    # Add basic story node properties

class ChoiceEdge(Edge):
    """A player-selectable transition between nodes."""
    # Add choice-specific properties like display text

class Domain:
    """Container for story-specific globals and templates."""
    # Minimal implementation for tracking global state and templates

    def get_globals(self):
        ...
