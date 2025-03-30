import yaml

import tangl.utils.setup_yaml


def test_dumper():
    s = {"xyz": "abc\ndef"}
    z = yaml.dump(s)

    assert z == """\
xyz: |-
  abc
  def
"""


