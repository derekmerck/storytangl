from tangl.ir.story_ir import BlockScript, StoryScript

class TweeExporter:
    """Export StoryScript to Twee format."""

    def export(self, script: StoryScript) -> str:
        """StoryScript → Twee text."""
        passages = []

        for scene in script.scenes.values():
            for block in scene.blocks.values():
                passages.append(self._block_to_twee(block))

        return '\n\n'.join(passages)

    def _block_to_twee(self, block: BlockScript) -> str:
        """BlockScript → :: PassageName syntax."""
        lines = []

        # Header with optional tags
        tags = f" [{' '.join(block.tags)}]" if block.tags else ""
        lines.append(f":: {block.label}{tags}")

        # Content
        if hasattr(block, 'text') and block.text:
            lines.append(block.text)

        # Actions as links
        if hasattr(block, 'actions'):
            for action in block.actions:
                text = action.text or 'Continue'
                target = action.successor
                lines.append(f"[[{text}->{target}]]")

        return '\n'.join(lines)