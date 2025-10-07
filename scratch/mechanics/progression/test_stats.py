import pytest
from enum import IntEnum

from scratch.progression.measures import Quality
from scratch.progression.measured_value import MeasuredValue as MV, NormalMVHandler, LogarithmicMVHandler
from scratch.progression.stats import HasStats
from scratch.progression.stat_domains import PsychosomaticStatDomain

@pytest.fixture
def linear_stat():
    return MV(10.0, measure=Quality)

@pytest.fixture
def logarithmic_stat():
    return MV(10.0, handler=LogarithmicMVHandler, measure=Quality)

@pytest.fixture
def normal_stat():
    return MV(10.0, handler=NormalMVHandler, measure=Quality)

class Character(HasStats):
    stat_domains = PsychosomaticStatDomain

@pytest.fixture()
def character():
    return Character()

def test_measure_enum():
    assert Quality.VERY_POOR == 1
    assert Quality.VERY_GOOD == 5

def test_stat_initialization(linear_stat):
    assert linear_stat.fv == 10.0
    assert linear_stat.qv == 3
    assert linear_stat.qv is Quality.AVERAGE

def test_logarithmic_stat_initialization(logarithmic_stat):
    assert logarithmic_stat.fv == 10.0
    assert logarithmic_stat.qv == 4  # it's actually 3.5 but rounds to 4
    assert logarithmic_stat.qv is Quality.GOOD

def test_normal_stat_initialization(normal_stat):
    assert normal_stat.fv == 10.0
    assert normal_stat.qv == 3
    assert normal_stat.qv is Quality.AVERAGE

def test_stat_addition(linear_stat):
    linear_stat += 5.0
    assert linear_stat.fv == 15.0
    assert linear_stat.qv == 4
    assert linear_stat.qv is Quality.GOOD

def test_stat_subtraction(linear_stat):
    linear_stat -= 5.0
    assert linear_stat.fv == 5.0
    assert linear_stat.qv == 2

def test_stat_comparison(linear_stat):
    assert linear_stat > 5.0
    assert linear_stat == 10.0
    assert linear_stat < 15.0

def test_logarithmic_stat_conversion(logarithmic_stat):
    assert LogarithmicMVHandler.qv_from_fv(logarithmic_stat.fv) == 4
    assert LogarithmicMVHandler.fv_from_qv(3) == LogarithmicMVHandler.b**(3-1)   # 2.1^2 ~ 4.5

def test_normal_stat_conversion(normal_stat):
    assert NormalMVHandler.qv_from_fv(normal_stat.fv) == 3
    assert NormalMVHandler.fv_from_qv(3) == 10.0

def test_has_stats_accessors(character):
    print( character.stats[PsychosomaticStatDomain.BODY] )
    print( character.body )
    assert character.body == Quality.AVERAGE, f"character.body should be Q.Average ({character.body})"

def test_has_stat_fv_increments(character):
    character.body += 5.0
    assert character.body.fv == 15.0
    assert character.body == Quality.HIGH

def test_has_stat_qv_increments(character):
    print(character.body.fv, character.body.qv)
    character.body += 2
    assert character.body.fv == 15.0
    assert character.body == Quality.HIGH


if __name__ == "__main__":
    pytest.main()
