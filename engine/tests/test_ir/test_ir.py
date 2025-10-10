from pprint import pprint

from tangl.ir.story_ir import StoryScript

def test_story_script_schema():
    # This basically just confirms that all the models resolve properly
    out = StoryScript.model_json_schema()
    pprint( out, indent=0, compact=True, width=100 )
