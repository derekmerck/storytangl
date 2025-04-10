"""
Given a dict with list items, return a list of all dicts from
the product of the list items.

{ a: [1,2]
  b: [3,4] }

->

[{a:1, b:3},
 {a:1, b:4},
 {a:2, b:3},
 {a:2, b:4}]

Useful for expanding kwargs
"""
import itertools

def dict_product(data: dict, ignore: list[str] = ()) -> list[dict]:
    list_items = { k: v for k, v in data.items() if isinstance(v, list) and k not in ignore}
    prod = itertools.product( *list_items.values() )
    res = [data | {k: v for k, v in zip(list_items.keys(), params)} for params in prod]
    return res
