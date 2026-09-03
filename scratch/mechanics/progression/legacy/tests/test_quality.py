import pytest
from tangl.utils.measure import Measure
from scratch.progression.measured_domains import MeasuredDomain
from scratch.progression.quality import Quality

def test_quality_addition_same_domain():
    q1 = Quality(Measure.MEDIUM, MeasuredDomain.BODY)
    q2 = Quality(Measure.SMALL, MeasuredDomain.BODY)
    q3 = q1 + q2
    assert q3.measure == Measure.MEDIUM
    assert q3.domain == MeasuredDomain.BODY
    q4 = q3 + q2
    assert q4.measure == Measure.LARGE

def test_quality_subtract_same_domain():
    q1 = Quality(Measure.MEDIUM, MeasuredDomain.BODY)
    q2 = Quality(Measure.VERY_SMALL, MeasuredDomain.BODY)
    q3 = q1 - q2
    assert q3.measure == Measure.MEDIUM
    assert q3.domain == MeasuredDomain.BODY
    q4 = q3 - q2
    assert q4.measure == Measure.SMALL

def test_quality_mult_same_domain():
    q1 = Quality(Measure.VERY_LARGE, MeasuredDomain.BODY)
    q2 = Quality(Measure.SMALL, MeasuredDomain.BODY)
    q3 = q1 * q2
    assert q3.measure == Measure.SMALL

def test_quality_addition_different_domain():
    q1 = Quality(Measure.MEDIUM, MeasuredDomain.BODY)
    q2 = Quality(Measure.SMALL, MeasuredDomain.MIND)
    with pytest.raises(ValueError):
        q1 + q2

def test_quality_subtraction_different_domain():
    q1 = Quality(Measure.MEDIUM, MeasuredDomain.BODY)
    q2 = Quality(Measure.SMALL, MeasuredDomain.MIND)
    with pytest.raises(ValueError):
        q1 - q2

def test_quality_mult_different_domain():
    q1 = Quality(Measure.MEDIUM, MeasuredDomain.BODY)
    q2 = Quality(Measure.SMALL, MeasuredDomain.MIND)
    with pytest.raises(ValueError):
        q1 * q2
