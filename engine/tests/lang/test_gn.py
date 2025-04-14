
from tangl.narrative.lang.gendered_nominals import gn, gendered_nominals, normalize_gn, is_xx_patterns

def test_gn():

    for m, f in gendered_nominals:
        for b in [True, False]:
            assert gn( m, b ) == f if b else m
            assert gn( f, b ) == f if b else m

    for w in ['cat', 'tree', 'run', 'Blue']:
        for b in [True, False]:
            assert gn( w, b) == w, "Should be no change if not in map."


def test_normalize_gn():

    print( is_xx_patterns )

    test_xx_str = "The Baroness of Foo went to see the maid, who was a bitch."
    expected_xy_str = "The Baron of Foo went to see the steward, who was a dog."

    res = normalize_gn(test_xx_str, False)
    print( res )
    assert res == expected_xy_str, "Result should match expected"

    test_xy_str = "The samurai had tea with the Czar of Russia."
    expected_xx_str = "The onna-musha had tea with the Czarina of Russia."

    res =normalize_gn(test_xy_str, True)
    print( res )
    assert res == expected_xx_str, "Result should match expected"

    test_xx_str = "Ms. Foo is the Queen."
    expected_xy_str = "Mr. Foo is the King."

    res =normalize_gn(test_xx_str, False)
    print( res )
    assert res == expected_xy_str, "Result should match expected"
