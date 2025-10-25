import pytest

from legacy.utils.log_int import LogInt, LogIntMeta
# todo: need edge case tests

LogInt10 = LogIntMeta('LogInt10', (LogInt,), {}, b=10)  # type: Type[LogInt]

def test_3_plus_3_is_4():

    # add mid in two different bases initialized from exponential space
    assert LogInt(3) + LogInt10(3) == 4
    # q.e.d., 3 + 3 == 4

def test_8_plus_1000_is_16():

    # add mid in two different bases initialized from linear space
    assert LogInt(8.) + LogInt10(1000.) == 16.
    # q.e.d., 8 + 1000 == 16

def test_mid_pl_mid_is_high():

    # add mid in two different bases initialized from strings
    assert LogInt("mid") + "mid" == "high"
    # q.e.d., "mid" + "mid" == "high"

def test_qmid_pl_qmid_is_qhigh():

    # add mid in two different bases initialized from qualities
    # note the quality scales are interchangeable in this case b/c cls.increments are the same
    assert LogInt(LogInt.Quality.MID) + LogInt10(LogInt10.Quality.MID) == LogInt.Quality.HIGH


def test_total_order():

    assert LogInt(3) == 3
    assert LogInt(3) >  LogInt(2)
    assert LogInt(3) >= LogInt(2)
    assert LogInt(3) == LogInt(10.)

    # But comparing in ev or lv space will give a strict comparison
    assert LogInt(3).ev < LogInt(10.).ev
    # midpoint in a different base, but slightly higher
    assert LogInt(3).ev < LogInt10(1001.).ev

    assert LogInt(3) <  LogInt.Quality.HIGH
    assert LogInt(3) <= LogInt.Quality.HIGH

    assert LogInt(3) == LogInt.Quality.MID

    LogInt_i7 = LogIntMeta("LogIntb3i7", (LogInt,), {}, increments=7)  # type: Type[LogInt]
    with pytest.raises(TypeError):
        assert LogInt(3) == LogInt_i7.Quality.MID
