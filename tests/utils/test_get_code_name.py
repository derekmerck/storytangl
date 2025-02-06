
from tangl.utils.get_code_name import get_code_name

def test_get_code_name_title_case():
    name = get_code_name(sub=False, morph=False)
    print( name )
    assert name.istitle()


def test_get_code_name(num_iters=5000):
    """
    This checks for less than 1 repeat per thousand over a larger sample size
    """
    names = set()
    repeats = 0

    for i in range(num_iters):
        name = get_code_name()
        if name in names:
            print(f"Yikes! {name} was duplicated (after {len(names)})")
            repeats += 1
        names.add(name)

    assert repeats <= num_iters/1000, f"Unfortunately, observed {repeats} repeated names of {num_iters}"
