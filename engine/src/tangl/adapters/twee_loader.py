from tangl.ir.story_ir import StoryScript

class TweeLoader:
    """Parse Twee text format into StoryScript."""

    def load(self, twee_text: str) -> StoryScript:
        """Twee text → script dict → StoryScript."""
        script_dict = self._parse_twee_to_dict(twee_text)
        return StoryScript.model_validate(script_dict)

    def _parse_twee_to_dict(self, text: str) -> dict:
        """
        Parse Twee into the SAME dict structure that YAML produces.

        This is the key insight - you're not creating a new IR,
        you're just providing an alternate parser for the same IR.
        """
        passages = self._extract_passages(text)

        # Convert to StoryScript dict format
        blocks = {}
        for name, passage in passages.items():
            blocks[name] = {
                'label': name,
                'text': '\n'.join(passage['content']),
                'actions': [
                    {'text': link['text'], 'successor': link['target']}
                    for link in passage['links']
                ],
            }
            if passage.get('tags'):
                blocks[name]['tags'] = passage['tags']

        return {
            'label': 'twee_import',
            'metadata': {'title': 'Imported from Twee'},
            'scenes': {
                'main': {
                    'label': 'main',
                    'blocks': blocks
                }
            }
        }