"""
Spellcheck for 'text' fields is embedded in the test scripts.  Add words by hand to the world pwl file.

If you want to do it by hand, here is an example snippit using `aspell` and `yq` ([yq][] from brew) that identifies potential misspellings in the `text` fields of a scene file.

[yq]: https://github.com/mikefarah/yq

```
yq e '.blocks[].text' <scene>.yaml | aspell -a | cut -d ' ' -f 2 | grep -v '*' | grep -v '^n[A-Z]'| grep -v '^$'
```

requirements: enchant (and lib)

Only called by manually for testing/validation
"""
import typing as typ
import pathlib
from collections import defaultdict
import os
import re

# Fix for python not finding arm64 binaries
import platform
if platform.machine() == "arm64" and platform.system() == "Darwin":
    # Using homebrew libenchant
    os.environ['PYENCHANT_LIBRARY_PATH'] = "/opt/homebrew/lib/libenchant-2.2.dylib"
import enchant
from enchant.checker import SpellChecker


errdict = typ.NewType("errdict", typ.Dict[str, int])


colors_pat = re.compile(r'#[a-fA-F\d]{6}')

def find_misspelled( str_, pwl: typ.Union[pathlib.Path, str]=None ) -> errdict:  # pragma: no cover
    if not str_:
        return {}

    if pwl:
        with open( pwl ) as f:
            _pwl = set( f.read().split("\n") )
            _pwl.discard('')
    else:
        _pwl = []

    def cardinal_err(err) -> str:
        # checks to see if this is part of a hyphenated word

        # todo: skip ok for now, but standardize it eventually
        if err.word.lower() == "ok":
            return False

        if err.trailing_context(1) == "-":
            nw = err.word + err.trailing_context(15)
            nw = nw.split(" ")[0]
            # print(f"Found hyphen after {err.word}, using {nw}")
            if nw not in _pwl:
                return nw
            return False
        if err.leading_context(1) == "-":
            nw = err.leading_context(15) + err.word
            nw = nw.split(" ")[-1]
            # print(f"Found hyphen before {err.word}, using {nw}")
            if nw not in _pwl:
                return nw
            return False
        return err.word

    # get rid of colors with multiple letters in a row
    str_ = colors_pat.sub("", str_)

    chkr = SpellChecker("en_US")
    if pwl:
        if isinstance(pwl, pathlib.Path):
            pwl = str(pwl)
        chkr.dict = enchant.DictWithPWL(tag="en_US", pwl=pwl)
    chkr.set_text( str_ )
    errs = defaultdict(int)
    for err in chkr:
        nw = cardinal_err(err)
        if nw:
            errs[nw] += 1
    return errs


def suggest_misspelled(errs: errdict, pwl=None ):  # pragma: no cover
    chkr = SpellChecker("en_US")
    if pwl:
        chkr.dict = enchant.DictWithPWL(tag="en_US", pwl=pwl)
    for k, v in errs.items():
        print( f"Not found ({v}): {k}: {chkr.dict.suggest(k)[:2] }?")
