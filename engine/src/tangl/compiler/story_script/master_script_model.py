from typing import Any

from tangl.story.story_script_models import StoryScript  # be cautious of circular imports here
from .script_metadata_model import ScriptMetadata

class MasterScript(StoryScript):

    metadata: ScriptMetadata

    @classmethod
    def model_json_schema(cls, **kwargs) -> dict[str, Any]:
        schema = super().model_json_schema(**kwargs)

        # from pprint import pprint
        # pprint( schema )

        defs = schema['$defs']

        # Add the IntelliJ injection info to the 'text' and 'comments' fields

        if 'BlockScript' in defs:
            defs['BlockScript']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        if 'text' in defs['ScriptMetadata']['properties']:
            defs['ScriptMetadata']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        if 'comments' in defs['ScriptMetadata']['properties']:
            defs['ScriptMetadata']['properties']['comments']['x-intellij-language-injection'] = "Markdown"
        else:
            # Handle the alias from text (public alias) -> comments (field name)
            defs['ScriptMetadata']['properties']['comments'] = \
                {'title': 'Comments',
                 'type': 'string',
                 'x-intellij-language-injection': 'Markdown'}

        # # todo: move this into passages format and override function
        # if 'PassageScript'in defs:
        #     defs['PassageScript']['properties']['text']['x-intellij-language-injection'] = "Markdown"

        return schema
