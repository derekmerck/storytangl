"""
Spell Check

- Attempts to render all label and text strings for a world
- Optionally spell checks all strings against world pwl
- Optionally grammar checks all strings with language-tool (TBD)
- Optionally checks for html correctness (missing tags, etc.)
- Outputs spelling, grammar, and tidy errors and total word counts

Depends on lang package dev reqs:
- [pyenchant](https://pyenchant.github.io/pyenchant/)
- `aspell` binary (`$brew install aspell`)
- a language-tool node
- pytidylib
"""

# todo: throw out anything in <span class="hob">.*</span>, assume its generated

from __future__ import annotations
from collections import defaultdict

import jinja2.exceptions

from tangl.core import Renderable
from tangl.story import Scene, Block
from tangl.world.world import World
from tangl.world.narrator.lang.ref_lex import find_misspelled, suggest_misspelled
from tidylib import tidy_fragment

CHECK_SPELLING = True   # check all strings against world pwl
CHECK_GRAMMAR = False   # check all strings
CHECK_TIDY = False      # check all strings for html correctness (finds missing /spans, etc)

def validate_scenes(wo: World):
    with wo.new_story() as ctx:

        total_words = 0
        composite_err_dict = defaultdict(int)
        sc: Scene

        for sc in ctx.get_scenes():
            # print(context.keys())
            sc.cast(force=True)  # force casting

            err_dict = defaultdict(int)
            words = 0
            bl: Block

            def count_words(go: Renderable) -> int:

                def c_(s: str) -> int:
                    if not s:
                        return 0
                    return len(s.split())

                words = 0
                try:
                    r = go.render()
                except jinja2.exceptions.UndefinedError as e:
                    print(e)
                    r = {}

                words += c_(r.get("label"))
                words += c_(r.get("text"))
                return words

            def check_obj(go: Renderable):
                # print( go.uid )
                try:
                    r = go.render()
                except jinja2.exceptions.UndefinedError as e:
                    print(e)
                    r = {}

                if CHECK_TIDY:
                    _text = r.get("text")  # deep_md( r.get("desc") )
                    fragment, errors_ = tidy_fragment(_text)
                    errors = []
                    for line in errors_.split("\n"):
                        if line.endswith("Warning: missing <!DOCTYPE> declaration") or \
                              line.endswith("Warning: plain text isn't allowed in <head> elements") or \
                              line.endswith("Warning: inserting missing 'title' element"):
                            continue
                        elif line:
                            errors.append( line )
                    if errors:
                        print( fragment )
                        print( errors )

                if CHECK_SPELLING:
                    ed = find_misspelled(r.get("label"), pwl=ctx.world.pwl)
                    for k, v in ed.items():
                        # print("label")
                        err_dict[k] += v
                        composite_err_dict[k] += v
                    ed = find_misspelled(r.get("desc"), pwl=ctx.world.pwl)
                    for k, v in ed.items():
                        # print("desc")
                        err_dict[k] += v
                        composite_err_dict[k] += v
                    return err_dict

            if not isinstance( sc.blocks, dict ):
                print(f"------------------\nMisformed Blocks in {sc.uid}:\n")
                print( sc )
                raise TypeError("Misformed blocks")

            for bl in sc.blocks.values():
                try:
                    check_obj(bl)
                except:
                    print(f"------------------\nBlock Error in {bl.path}:\n")
                    print(bl)
                words += count_words(bl)

                for ac in bl.actions:
                    check_obj(ac)
                    words += count_words(ac)

            total_words += words

            if err_dict:
                print(f"\n## Possible misspellings in {sc.uid}\n----------")
                suggest_misspelled(err_dict)

                for k, v in err_dict.items():
                    composite_err_dict[k] += v

        print(f"Total words in scenes: {total_words}")
        return total_words


if __name__ == "__main__":

    World.load_all_worlds()

    total_words = 0
    for wo_ in World.ls():
        wo = World[wo_]
        total_words += validate_scenes(wo)

    print(f"Total words in all worlds: {total_words}")
