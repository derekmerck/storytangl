from pprint import pprint

from legacy.utils.deep_md import deep_md

def test_deep_md():

    data = [{"text": "*hello*",
             "item": None},
            [{"label": "*hello*",
              "item": [{"text": "*hello*",
                        "label": 28}]}],
            28]

    res = deep_md(data)
    pprint(res)

    assert res == [{'text': '<p><em>hello</em></p>\n',
                    'item': None},
                   [{'label': '<em>hello</em>',
                     'item': [{'text': '<p><em>hello</em></p>\n',
                               'label': 28}]}],
                   28]


if __name__ == "__main__":
    test_deep_md()
