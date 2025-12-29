# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from tangl.info import __author__, __author_email__, __title__, __version__
import tangl.core.entity
import tangl.core.entity.handlers
import tangl.core.graph
import tangl.core.graph.handlers
import tangl.core.handler

project = __title__
copyright = f'2024, {__author__}'
author = __author__
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'myst_parser',
    'sphinxcontrib.autodoc_pydantic',
    'sphinx_autodoc_typehints',
    'sphinx_markdown_builder'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

autodoc_member_order = 'bysource'
autoclass_content = 'class'
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_summary_list_order = "bysource"
autodoc_pydantic_model_member_order = "bysource"
# autodoc_pydantic_validator_replace_signature = False
autodoc_pydantic_field_swap_name_and_alias = True
autodoc_pydantic_field_list_validators = False
autodoc_pydantic_model_show_json = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = 'sphinx_rtd_theme'
html_theme = 'furo'
html_static_path = ['_static']

# Create markdown output with
# $ PYTHONPATH="./engine" sphinx-build -M markdown  ./docs ./docs/_md

# Notes:
# - supress json with `-D autopydantic_model_show_json = False`
# - discard the furo declarations in _md/_static
