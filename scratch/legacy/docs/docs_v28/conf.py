# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('.'))  # Adjust the path as necessary

import toml

project = 'StoryTangl'
copyright = '2023, TanglDev'
author = 'TanglDev'

# Read the pyproject.toml file
with open('../pyproject.toml', 'r') as f:
    pyproject = toml.load(f)

# Extract the version
release = pyproject['tool']['poetry']['version']

# -- General configuration ---------------------------------------------------

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              # "myst_parser",
              "sphinx.ext.autosectionlabel",
              'sphinx.ext.autodoc.typehints',
              "sphinxcontrib.mermaid",
              'sphinxcontrib.autodoc_pydantic',
              "sphinxcontrib.openapi"]

autodoc_typehints = 'none'
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'undoc-members': True,
    'inherited-members': 'BaseModel',
    'exclude-members': 'model_dump, model_config, model_fields'
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_book_theme'
# html_theme = 'alabaster'
html_static_path = ['_static']
