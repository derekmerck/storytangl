import types

import yaml

from legacy.utils.bunch import Bunch, Spans

# language=YAML
src = """
---
backend_ui:
  ICON:
    ring: ring
    car:  car

  SPAN:
    player: '#b94f3a'  # brand
    guy:    lightgray
    girl:   pink
"""


def test_spans():
    backend_ui = yaml.safe_load(src)['backend_ui']
    SPAN = Spans( backend_ui['SPAN'] )
    ICON = Bunch( backend_ui['ICON'] )

    print(SPAN.END)
    print(SPAN.__dict__)
    print(SPAN.PLAYER)
    print(SPAN.pov)
    print(SPAN.P)
    print(SPAN.END)
    print(SPAN.FOR( types.SimpleNamespace( text_color="black" )))

    print(ICON.ring)
    print(ICON.car)


if __name__ == "__main__":
    test_spans()
