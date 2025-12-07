import json

from tangl.scripting.master_script_model import MasterScript

import pytest


def test_master_script_schema():
    schema = MasterScript.model_json_schema()
    print(json.dumps(schema, indent=2))

    assert schema['$defs']['BlockScript']['properties']['text']['x-intellij-language-injection'] == "Markdown"


