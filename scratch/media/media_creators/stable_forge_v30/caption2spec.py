"""
cap2prompt(caption, locs, roles, shot_type=narrative)

The md image caption provides a succinct, human-legible description
of a shot.

Given the context of the shot type and scene roles and locations,
a complete stableforge prompt spec (who, how, what, where, when)
can be inferred from the caption.

establishing: where; when
  - "a quaint suburban house; {late night}"
  - "the <lair>; {morning}"

narrative: who; how; what; where; when
  - "a teenage babysitter {with blue hair} {wearing XYZ}; peeks out from a doorway; {at a suburban house}; {late night}"
  - "<britney> {with blue hair} {wearing XYZ}; peeks out from a doorway; {at the <lair>}, {morning}"
"""
from pathlib import Path

whens = ['early morning', 'morning', 'daytime', 'afternoon', 'night', 'late night']

def when( phrase: str ):
    for w in whens:
        if w in phrase:
            return w

def where( phrase: str, locs: list ):
    locs = locs or []
    for l in locs:
        if l['uid'] in phrase:
            123

def cap2prompt(im: dict, block: dict, roles: list[dict] = None, locs: list[dict] = None) -> dict:

    if not im.get('caption'):
        return

    # infer a uid
    uid = im.get('uid') or Path(block['uid']).stem

    if im.get('shot_type').startswith('est') or 'establish' in uid:
        shot_type = 'establish'
    else:
        shot_type = 'narrative'

    parts = im['caption'].split(';')

    where = None
    when = None

    who = None
    wearing = None
    style = None
    doing = None

    if shot_type == 'establish':
        if len(parts) == 1:
            where = parts[0]
        elif len(parts) == 2:
            where, when = parts

    else:
        if len(parts) == 2:
            who, doing = parts
        elif len(parts) == 2:
            where, when = parts

    # normalize locs
    for loc in locs:
        if loc.uid in where:
            where = 0

    # normalize whens
    for w in whens:
        if w in when:
            when = w

    spec = {
        'uid': uid,
        'shot_type': 'establish',
        'where': im.get('caption')
    }
    return spec


for role in []:
    if role['uid'] in {}.get('caption', []):
        who = role['uid']

