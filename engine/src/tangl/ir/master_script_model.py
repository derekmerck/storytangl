from typing import Any

from .base_script_model import BaseScriptItem
from .script_metadata_model import ScriptMetadata

class MasterScript(BaseScriptItem):

    metadata: ScriptMetadata

    @classmethod
    def model_json_schema(cls, **kwargs) -> dict[str, Any]:
        schema = super().model_json_schema(**kwargs)

        # from pprint import pprint
        # pprint( schema )

        defs = schema['$defs']

        # Add the IntelliJ injection info to the 'text' and 'comments' fields

        if 'BlockScript' in defs:
            defs['BlockScript']['properties']['content']['x-intellij-language-injection'] = "Markdown"

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
