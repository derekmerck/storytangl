from pathlib import Path
from typing import *

import yaml


def deep_merge( source, update ):

    if not isinstance( update, dict ):
        return update

    for k, v in update.items():
        if k in source and isinstance(v, dict):
            deep_merge( source[k], v )
        elif k in source and isinstance(v, list):
            if isinstance( v[0], dict):
                for ss, vv in zip(source[k], v):
                    deep_merge(ss, vv)
            else:
                source[k] += v
        elif isinstance(source, str):
            pass  # This is a consumes str, could compress it out but meh
        else:
            source[k] = v


def glob2dict(fp: Path, _glob: Union[str, List[str]]):

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
                if 'uid' not in s:
                    print("No uid", s)
                    continue
                uid = s['uid']
                if uid not in res:
                    res[uid] = s
                else:
                    deep_merge( res[uid], s )
    return res