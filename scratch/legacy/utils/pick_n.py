"""
Pick-n-w-Overlap

Consider the task of picking a unique sample from each of three
overlapping populations.

[A,B], [B,C], [A,D]

Naively picking A from set 3 and B from set 2 would leave no
possible candidates in set 1.  However, if we start by picking as
specifically as possible, with D and C, we can satisfy the
conditions.

In order to use this, first divvy your possibilities up into bags,
where the objects in each bag all satisfy one of the condition sets.

Then pull items in order from most specific to most general.

This is a useful algorithm when casting scenes with many actors who 
might each fill multiple roles.
"""

import typing as typ
from collections import Counter

def pick_n_w_overlap(bags: typ.List) -> typ.Optional[typ.List]:
    # Create specificity matrix
    generality = Counter()
    for b in bags:
        for item in b:
            generality[item] += 1

    # Sort by specificity (smallest to largest generalizability)
    specificity = generality.most_common()
    specificity.reverse()
    result = [False for i in range(len(bags))]

    for val, _count in specificity:
        if all(result):
            # print(f"Skipping item {val} as all bags are picked")
            break
        for i, b in enumerate(bags):
            if result[i]:
                # print(f"Skipping bag {i}, already picked as {result[i]}")
                continue
            if val in b:
                # print(f"Picked {val} for bag {i}, skipping to next item")
                result[i] = val
                break
            # print(f"Uninteresting {val} for {i}")

    if all(result):
        return result

