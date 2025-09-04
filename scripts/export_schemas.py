"""
Generate json schemas for the tangl-script object types.

Usage:
$ python tangl.script.export_schema > tangl_schema.json

Individual files for multi-file scripts are additionally written to the
package directory `extras/schemas`.  They can then be associated with
file name patterns in an IDE.

e.g., `extras/schemas/tangl_actor.json` -> `**/resources/actors/*.yaml`
"""
import re
import json
from pathlib import Path
from typing import Type

from tangl.compiler.script_metadata_model import ScriptMetadata
from tangl.compiler.master_script_model import MasterScript
from tangl.story.story_script_models import ActorScript, PlaceScript, SceneScript

EXTRAS_DIR = Path(__file__).parent.parent / "extras/schemas"

def update_schemas():

    with open(EXTRAS_DIR / "tangl_script.json", "w") as f:
        schema = MasterScript.model_json_schema()
        json.dump(schema, f)

    with open(EXTRAS_DIR / "tangl_actor.json", "w") as f:
        schema = ActorScript.model_json_schema()
        json.dump(schema, f)

    with open(EXTRAS_DIR / "tangl_place.json", "w") as f:
        schema = PlaceScript.model_json_schema()
        json.dump(schema, f)

    with open(EXTRAS_DIR / "tangl_scene.json", "w") as f:
        schema = SceneScript.model_json_schema()
        json.dump(schema, f)

    with open(EXTRAS_DIR / "tangl_info.json", "w") as f:
        schema = ScriptMetadata.model_json_schema()
        json.dump(schema, f)

def extract_first_word(camelcase_string):
    # This regex matches the first group of characters where the first character is uppercase
    # and is followed by zero or more lowercase characters.
    match = re.match(r'([A-Z][a-z]*)', camelcase_string)
    if match:
        return match.group(1)
    return None  # Return None or raise an error if no match is found


def update_subclass_schemas(base_script = MasterScript):

    for scls in base_script.__subclasses__():
        print( scls )

        scls_name = extract_first_word(scls.__name__).lower()
        if scls_name == "Master":
            scls_name = "Script"

        fn = f"tangl_{scls_name}.json"

        with open(EXTRAS_DIR / fn, "w") as f:
            schema = scls.model_json_schema()
            json.dump(schema, f)


if __name__ == "__main__":
    print(MasterScript.model_json_schema())

    if not EXTRAS_DIR.is_dir():
        EXTRAS_DIR.mkdir(exist_ok=True)

    update_schemas()
    update_subclass_schemas()
