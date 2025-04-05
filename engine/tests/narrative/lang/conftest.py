import pytest

from narrative.lang._api_samples.mw_samples import sample_data as mw_sample_data_
from narrative.lang._api_samples.verbix_samples import sample_raw_html1 as verbix_sample_raw_html1_, sample_raw_html2 as verbix_sample_raw_html2_

@pytest.fixture
def mw_sample_data():
    return mw_sample_data_

@pytest.fixture
def verbix_sample_raw_html1():
    return verbix_sample_raw_html1_

@pytest.fixture
def verbix_sample_raw_html2():
    return verbix_sample_raw_html2_
