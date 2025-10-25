

import yaml


def join(ldr, node):
    l = []
    for e in ldr.construct_sequence(node, deep=True):
        if type(e) is tuple and e[0] == 'splat':
            l.extend(e[1][0])
        elif type(e) is dict and e.get('<', None) is not None:
            l.extend(e['<'])
        else:
            l.append(e)
    return l

yaml.add_constructor('tag:yaml.org,2002:seq', join)

