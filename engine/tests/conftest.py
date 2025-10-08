import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("markdown_it").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)

# from pathlib import Path
# import pytest
# import yaml
#
# test_resources = Path(__file__).parent / 'resources'
#
# @pytest.fixture(scope='session')
# def my_script_data():
#     fp = test_resources / 'my_script.yaml'
#     with open(fp) as f:
#         data = yaml.safe_load(f)
#     return data
