import hashlib

import re
from copy import copy
import sys
import importlib
import types
from pathlib import Path
from typing import *
import pickle

import yaml

from tangl.31.actor import Actor
from tangl.31.asset import Unit, Commodity
from tangl.31.game.management import Generator
from tangl.31.entity.factory import EntityTemplates, EntityFactory
from tangl.31.scene import Scene, Hub
from tangl.31.svg import SvgFactory
from tangl.31.utils.glob2dict import glob2dict
from tangl.31.utils.singleton import SingletonsManager
from tangl.31.utils.hash_dir import hash_dir


class WorldLoader:

    # Caching singletons is hard
    # @classmethod
    # def _uncache_world_params(cls, base_dir) -> Dict:
    #     val = hash_dir(base_dir)
    #     cache_path = Path(base_dir) / ".cache" / f"{val}.pkl"
    #     if cache_path.is_file():
    #         print( "loading from cache" )
    #         with open( str( cache_path ), 'rb' ) as f:
    #             return pickle.load( f )
    #     raise FileNotFoundError
    #
    # @classmethod
    # def _cache_world_params(cls, data, base_dir):
    #     val = hash_dir(base_dir)
    #     cache_path = Path(base_dir) / ".cache" / f"{val}.pkl"
    #     cache_path.parent.mkdir(exist_ok=True)
    #     with open( cache_path, "wb" ) as f:
    #         pickle.dump( data, f )

    @classmethod
    def _mk_entity_factory(cls, entity_templates: EntityTemplates) -> EntityFactory:
        entity_factory = EntityFactory(templates=entity_templates)
        entity_factory.add_entity_class(Actor)  # Override these class types in _init_world, if required
        entity_factory.add_entity_class(Scene)
        entity_factory.add_entity_class(Hub)
        return entity_factory

    @classmethod
    def _mk_asset_manager(self, entity_templates: EntityTemplates) -> SingletonsManager:
        asset_manager = SingletonsManager()
        asset_manager.add_singletons_cls(Unit)
        asset_manager.add_singletons_cls(Commodity)
        asset_manager.add_singletons_cls(Generator)

        for k, v in entity_templates.items():
            if k[0] in ["Unit", "Commodity", "Generator"]:
                asset_manager.new_instance(k[0], k[1], **v)

        return asset_manager

    default_templates_paths: ClassVar[Dict[str, List]] = {
        'Scene': ["./scenes/**/*.yaml"],
        'Hub':   ["./hubs/**/*.yaml"],
        'Actor': ["./phenotypes/**/*.yaml"],
        'Commodity': ["./commodities/**/*.yaml"],
        'Unit':  ["./units/**/*.yaml"]
    }
    default_scene_art_path: ClassVar[str] = "./scene_art.svg"
    default_hooks_path: ClassVar[str] = "./hw1"

    @classmethod
    def _mk_entity_templates(cls, data) -> EntityTemplates:
        templates = EntityTemplates()
        for (entity_family, uid), templ in data.items():
            templates.add_template(entity_family, **templ)
        return templates

    @classmethod
    def _load_entity_templates(cls, base_path: Path, templates_paths: dict[str, str]) -> EntityTemplates:
        data = {}
        for k, v in templates_paths.items():
            templs = glob2dict(base_path, v)
            for uid, templ in templs.items():
                data[k, uid] = templ
        templs = cls._mk_entity_templates( data )
        return templs

    @classmethod
    def _load_hooks(cls, fp: Path, hooks_path: Path) -> types.ModuleType:

        hook_path = (fp / hooks_path / "__init__.py").resolve()
        try:
            with open(hook_path) as f:
                s = f.read()
                m = re.findall(r'__name__ = "(.*)"', s)
                pkg_name = m[0]
        except (FileNotFoundError, IndexError):
            raise KeyError(f"Can't parse module name from {hook_path}")

        spec_ = importlib.util.spec_from_file_location(pkg_name, hook_path)
        pkg = importlib.util.module_from_spec(spec_)
        sys.modules[pkg.__name__] = pkg
        spec_.loader.exec_module(pkg)

        return pkg

    @classmethod
    def load(cls, base_path: Union[Path, str] = None,
             ignore_missing_hooks: bool=False,
             no_cache=True) -> "World":


        if isinstance( base_path, str ):
            base_path = Path( base_path )

        if not base_path.is_dir():
            from tangl.31.config import TANGL_WORLDS_PATH
            base_path = TANGL_WORLDS_PATH / base_path
            if not base_path.is_dir():
                raise FileNotFoundError

        with open( base_path / "world.yaml" ) as f:
            spec = yaml.safe_load( f )
            # spec includes entries for uid, label, desc, spans, icons;
            # templates_paths and backend_ui are popped and decomposed

        uid = spec['uid']
        label = spec.get('label', uid)
        entry = spec.get('entry', 'main_menu')
        info = spec.get('info')
        pwl = Path.resolve( base_path / spec.get('pwl') )

        templates_paths = copy( cls.default_templates_paths )
        if "templates_paths" in spec:
            templates_paths = templates_paths | spec.pop( "templates_paths" )
        entity_templates = cls._load_entity_templates( base_path, templates_paths )

        if "backend_ui" in spec:
            backend_ui = spec.pop( "backend_ui" )
        else:
            backend_ui = {}

        hooks_path = spec.get("hw1", cls.default_hooks_path)
        pkg = cls._load_hooks( base_path, hooks_path )

        scene_art_path = spec.get("scene_art", cls.default_scene_art_path )
        try:
            scene_art = SvgFactory.from_file( base_path / scene_art_path, preserve_styles=True )

        except FileNotFoundError:
            scene_art = None
            print( f"No scene art found for {spec['uid']} at {base_path / scene_art_path}")

        params = {'uid': uid,
                  'base_path': base_path,
                  'label': label,
                  'entry': entry,
                  'info': info,
                  'hw1': pkg,
                  'pwl': pwl,
                  **backend_ui,
                  'scene_art': scene_art}

        entity_factory = cls._mk_entity_factory( entity_templates )
        asset_manager = cls._mk_asset_manager( entity_templates )

        from .world import World
        wo = World( **params,
                    entity_factory = entity_factory,
                    asset_manager = asset_manager,
                    ignore_missing_hooks=ignore_missing_hooks )

        return wo
