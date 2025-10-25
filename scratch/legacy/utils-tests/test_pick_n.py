from legacy.utils.pick_n import pick_n_w_overlap


def test_pick_n():
    bags = [ ["A", "B", "C", "Z"],
             ["A", "C", "D", "E", "F", "Z"],
             ["B", "D", "Z"],
             ["A", "D", "Z"]]
    assert( pick_n_w_overlap(bags) )

    bags = [ ["A", "B"],
             ["A", "C", "D", "E", "F", "Z"],
             ["A", "B"],
             ["A", "B"]]
    # can't satisfy -- 3 require either A or B
    assert( not pick_n_w_overlap(bags) )


if __name__ == "__main__":
    test_pick_n()
