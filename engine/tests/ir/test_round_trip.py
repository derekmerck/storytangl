from copy import deepcopy
from pprint import pprint

import pytest
import yaml

from tangl.ir.core_ir import MasterScript
from tangl.ir.story_ir import StoryScript, SceneScript

def dict_compare(d1, d2):
    """Recursively compares two dictionaries and returns the differences."""
    if d1 == d2:
        return None  # Dictionaries are identical

    diffs = {}
    # Find keys in d1 not in d2
    for k, v in d1.items():
        if k not in d2:
            diffs[k] = ('missing in second', v)
        elif v != d2[k]:
            if isinstance(v, dict) and isinstance(d2[k], dict):
                nested_diff = dict_compare(v, d2[k])
                if nested_diff:
                    diffs[k] = ('nested diff', nested_diff)
            else:
                diffs[k] = ('differing values', v, d2[k])

    # Find keys in d2 not in d1
    for k, v in d2.items():
        if k not in d1:
            diffs[k] = ('missing in first', v)

    return diffs


def test_yaml_core_script_roundtrips():
    """
    YAML → StoryScript → YAML should be lossless.

    Demonstrates that the template classes ARE the IR

    YAML text → dict → StoryScript (IR) → dict → YAML text
         ↑                                      ↑
      (lossy)                              (lossless!)
    """

    original_yaml = """
    label: test_story
    metadata:
      title: Test Story
      author: Tdv
    templates:
      intro:
        label: intro
        templates:
          start:
            label: start
            text: You wake up.
            templates:
              - text: Look around
                successor: intro.look
          look:
            label: look
            text: It's a room.
    """

    # Parse
    original_dict = yaml.safe_load(original_yaml)
    script = MasterScript.model_validate(deepcopy(original_dict))

    # Export
    exported_dict = script.unstructure_as_template()
    cmp = dict_compare(original_dict, exported_dict)
    pprint(original_dict, indent=1, width=90)
    print("----------")
    pprint(exported_dict, indent=1, width=90)
    print("----------")
    pprint( cmp, indent=1, width=90 )

    assert cmp is None

    exported_yaml = yaml.dump(exported_dict, sort_keys=False)
    # Re-parse
    reparsed_dict = yaml.safe_load(exported_yaml)
    reparsed_script = MasterScript.model_validate(reparsed_dict)

    # Compare content hashes (should be identical)
    assert script.content_hash == reparsed_script.content_hash

    # Can compare with eq
    assert script == reparsed_script


def test_yaml_story_script_roundtrips():
    """Full StoryScript with scenes/blocks/actors should round-trip."""

    original_yaml = """
    label: test_story
    metadata:
      title: Test Story
      author: Tdv
    templates:
      global_guard:
        obj_cls: tangl.story.concepts.actor.actor.Actor
        archetype: guard
        hp: 50
    scenes:
      intro:
        label: intro
        templates:
          village_guard:
            obj_cls: tangl.story.concepts.actor.actor.Actor
            archetype: guard
            hp: 75
        blocks:
          start:
            label: start
            text: You wake up in the village.
            actions:
              - text: Look around
                successor: intro.look
          look:
            label: look
            text: You see a guard.
            templates:
              local_item:
                obj_cls: tangl.story.concepts.asset.asset.Asset
                label: sword
    """

    original_dict = yaml.safe_load(original_yaml)
    script = StoryScript.model_validate(deepcopy(original_dict))

    assert script.scenes['intro'].label == "intro"
    assert isinstance(script.scenes['intro'], SceneScript)
    from tangl.story.episode import Scene
    assert script.scenes['intro'].obj_cls == Scene

    exported_dict = script.unstructure_as_template()

    # Should be identical
    assert dict_compare(original_dict, exported_dict) is None

    # Content hash stable
    reparsed = StoryScript.model_validate(exported_dict)
    assert script.content_hash == reparsed.content_hash
