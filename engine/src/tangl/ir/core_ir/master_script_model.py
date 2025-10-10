from typing import Any

from .base_script_model import BaseScriptItem
from .script_metadata_model import ScriptMetadata

class MasterScript(BaseScriptItem):
    # Has metadata and subclass defined sections

    metadata: ScriptMetadata

    @classmethod
    def model_json_schema(cls, **kwargs) -> dict[str, Any]:
        schema = super().model_json_schema(**kwargs)

        # from pprint import pprint
        # pprint( schema )

        defs = schema['$defs']

        # Clean up Tag definitions everywhere
        def clean_tags_schema(obj):
            """Recursively remove verbose Enum descriptions from tags fields."""
            if isinstance(obj, dict):
                # If this is a tags field definition
                if 'title' in obj and obj.get('title') == 'Tags':
                    if 'anyOf' in obj:
                        for variant in obj['anyOf']:
                            if variant.get('type') == 'array' and 'items' in variant:
                                items = variant['items']
                                if 'anyOf' in items:
                                    # Replace the anyOf with a simple string/int schema
                                    variant['items'] = {
                                        'anyOf': [
                                            {'type': 'string'},
                                            {'type': 'integer'}
                                        ]
                                    }

                # Recurse through all nested dicts
                for key, value in obj.items():
                    clean_tags_schema(value)

            elif isinstance(obj, list):
                for item in obj:
                    clean_tags_schema(item)

        clean_tags_schema(schema)

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
