
import sys
import importlib
from typing import *
from pathlib import Path
import re
import types

import yaml

from tangl.31.svg import SvgFactory

if TYPE_CHECKING:  # pragma: no cover
    from .world import World
else:
    World = object

class WorldLoader(World):

    # default file locations, override these for custom worlds


    @staticmethod
    def glob_to_dict(fp: Path, _glob: Union[str, List[str]]):
        if _glob is None:
            return {}
        fp = Path(fp)

        # match multiple patterns if given a list
        if isinstance(_glob, str):
            _glob = [_glob]
        fps = []
        for g in _glob:
            fps += fp.glob(g)

        res = {}
        for _fpp in fps:
            with open(_fpp) as f:
                specs = yaml.safe_load_all(f)
                for s in specs:
                    uid = s['uid']
                    if uid not in res:
                        res[uid] = s
                    else:
                        deep_merge( res[uid], s )
        return res


    @staticmethod
    def load_hooks(fp: Path,
                   hooks_dir: Path) -> types.ModuleType:

        hook_path = ( fp / hooks_dir / "__init__.py" ).resolve()
        try:
            with open(hook_path) as f:
                s = f.read()
                m = re.findall(r'__name__ = "(.*)"', s)
                pkg_name = m[0]
        except (FileNotFoundError, IndexError):
            raise KeyError(f"Can't parse module name from {hook_path}")

        spec = importlib.util.spec_from_file_location(pkg_name, hook_path)
        pkg = importlib.util.module_from_spec(spec)
        sys.modules[pkg.__name__] = pkg
        spec.loader.exec_module(pkg)

        return pkg

    @staticmethod
    def load_scene_art(fp: Path,
                       art_dir: Path) -> 'SvgFactory':

        svg_path = ( fp / art_dir ).resolve()

        scene_art = SvgFactory.from_file(
                str(svg_path),
                preserve_styles=True)
        return scene_art

    @classmethod
    def load_world( cls: 'World', fp: Path) -> 'World':

        fp = Path(fp)

        world_spec = cls.load_world_spec(fp)

        templs = world_spec['templates']
        scene_templs = cls.glob_to_dict(fp, templs.get('Scene'))
        hub_templs = cls.glob_to_dict(fp, templs.get('Hub'))
        actor_templs = cls.glob_to_dict(fp, templs.get('Actor'))
        asset_templs = cls.glob_to_dict(fp, templs.get('Assets'))
        unit_templs = cls.glob_to_dict(fp, templs.get('Unit'))

        hooks = cls.load_hooks( fp, world_spec['hw1'])
        if "scene_art" in world_spec:
            scene_art = SvgFactory.from_file( fp / world_spec['scene_art'],
                                              preserve_styles=True )
        else:
            scene_art = None
        pwl = world_spec.get('pwl')
        if pwl:
            pwl = fp / pwl

        return cls(
            uid=world_spec['uid'],
            label=world_spec['label'],
            info=world_spec['info'],
            entry=world_spec['entry'],
            base_path=fp,
            backend_ui=world_spec['backend_ui'],
            hooks=hooks,
            scene_art=scene_art,
            pwl=pwl,
            scene_templs=scene_templs,
            hub_templs=hub_templs,
            actor_templs=actor_templs,
            asset_templs=asset_templs,
            unit_templs=unit_templs)


