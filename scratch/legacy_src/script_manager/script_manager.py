from __future__ import annotations
from typing import ClassVar, TypeVar, TYPE_CHECKING
from importlib import resources as resources_
from pathlib import Path
from collections import defaultdict
import logging

import yaml

from tangl.type_hints import UniqueLabel, Pathlike, ClassName, Locals
from .script_models import StoryScript, StoryMetadata

StringsMap = dict[UniqueLabel, str]
logger = logging.getLogger("tangl.script")

ScriptManagerType = TypeVar("ScriptManagerType", bound='ScriptManager')

if TYPE_CHECKING:
    from tangl.story.scene.script_models import *
    from tangl.story.actor.script_models import *
    from tangl.story.asset.script_models import *
    from tangl.story.place.script_models import *

class ScriptManager:

    def __init__(self, script: StoryScript):
        self.script = script

    script_model: ClassVar[type[StoryScript]] = StoryScript

    @classmethod
    def from_dict(cls: ScriptManagerType, script_dict: dict) -> ScriptManagerType:
        script = cls.script_model(**script_dict)
        return cls(script=script)

    @classmethod
    def from_text(cls: ScriptManagerType, script_text: str) -> ScriptManagerType:
        from tangl.utils.load_yaml_resource import load_yaml_text
        script_dict = load_yaml_text(script_text)
        # script_dict = yaml.safe_load(script_text)
        return cls.from_dict(script_dict)

    @classmethod
    def from_file(cls: ScriptManagerType,
                  resources: str = None,
                  script_file: Pathlike = None ):
        if resources:
            print( resources )
            base_path = Path(resources_.files(resources))
        else:
            base_path = Path()
        if not script_file.endswith('.yaml'):
            script_file += ".yaml"
        with open(base_path/script_file) as f:
            script_text = f.read()
        return cls.from_text(script_text)

    @classmethod
    def from_files(cls: ScriptManagerType,
                   resources: str = None,
                   files: Pathlike = None,
                   sections: dict = None,
                   metadata: Pathlike | dict = None) -> ScriptManagerType:
        """
        Multi-file story format loader reads story templates by section from a map
        of globs.

        :param str resources: importlib resources location, `world1.resources`
        :param str files: search path to resources directory
        :param dict sections: mapping of section keys to path globs, `{ section_key: [path-glob, ...], ... }`

        :raises ValueError: If both `resources` and `files` are specified

        If `sections` is not specified or if _neither_ `resources` nor `files` are
        specified, it silently passes and presumably defers loading to a plugin.
        """
        if not sections:
            # no sections
            return
        if resources:
            if files:
                raise ValueError("Use only one of `files` or `resources`")
            files = resources_.files(resources)
        if not files:
            return

        files = Path(files)
        script_dict = dict()  # of format: { scenes: { items } }
        for section, globs in sections.items():
            items = defaultdict(dict)  # of format: { uid: **data, ... }
            for glob in globs:
                fps = files.glob(glob)
                for fp in fps:
                    with open(fp, 'r') as f:
                        # Load all documents in the file
                        documents = yaml.load_all(f, Loader=yaml.FullLoader)
                        for doc in documents:
                            if not doc:
                                continue
                            # Check that the document is a dictionary
                            if not isinstance(doc, dict):
                                raise ValueError(f"Invalid document in {fp}: {doc}")
                            try:
                                items[doc['label']].update(doc)
                            except Exception as e:
                                logger.error("Error: Script error in doc")
                                logger.error(doc)
                                raise
            script_dict[section] = dict(items)

        if isinstance(metadata, dict):
            pass
        elif isinstance(metadata, str | Path):
            fp = files / metadata
            with open(fp, 'r') as f:
                metadata = yaml.safe_load(f)

        label = metadata.pop('label')
        script_dict['label'] = label
        script_dict['metadata'] = metadata

        return cls.from_dict(script_dict)

    @classmethod
    def _strings_map(cls, script) -> StringsMap:
        res = {}
        for sc_l, sc in script.scenes.items():
            l = [sc_l]
            if sc.text:
                res["/".join(l)] = sc.text
            sc_blocks = sc.blocks or {}
            for bl_l, bl in sc_blocks.items():
                l.append( bl_l )
                if bl.text:
                    res["/".join(l)] = bl.text
                for i, ac in enumerate( bl.actions or [] ):
                    l.append( f'ac-{i}' )
                    if ac.text:
                        res["/".join(l)] = ac.text
                    l.pop()  # action
                l.pop()  # bl
            l.pop()   # sc
        return res

    def strings_map(self) -> StringsMap:
        """A string map is useful for translations and compact story representations that refer text fields back to the world's string-map."""
        return self._strings_map(self.script)

    @classmethod
    def get_script_schema(cls, **kwargs) -> dict:
        """The script json-schema can be used for error checking while authoring."""
        return cls.script_model.model_json_schema(**kwargs)

    # Script accessors

    def metadata(self) -> StoryMetadata:
        return self.script.metadata

    def globals(self) -> Locals:
        return self.script.globals

    # The four cardinal types of story objects

    def scenes_data(self) -> list[dict]:
        if self.script.scenes:
            return [sc.model_dump() for sc in self.script.scenes.values()]
        return []

    def actors_data(self) -> list[dict]:
        if self.script.actors:
            return [ac.model_dump() for ac in self.script.actors.values()]
        return []

    def places_data(self) -> list[dict]:
        if self.script.places:
            return [loc.model_dump() for loc in self.script.places.values()]
        return []

    def assets_data(self) -> list[dict]:
        raise NotImplemented
