import pytest

from tangl.utils.ordered_tuple_dict import OrderedTupleDict

@pytest.fixture()
def data():
    data = OrderedTupleDict()
    data['a'] = 1
    data['b'] = 2, {'style': 'blah'}
    data['c'] = 3, 'abc', {'style': 'blah'}
    return data

def test_otd_flattening(data):

    data_flat = data.to_list()
    print(data_flat)
    data_restored = OrderedTupleDict.from_list(data_flat)
    print(data_restored)
    assert data_restored == data

def test_otd_json(data):
    data_flat = data.to_json()
    print(data_flat)
    data_restored = OrderedTupleDict.from_json(data_flat)
    print(data_restored)
    assert data_restored == data
