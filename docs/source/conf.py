# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
import os
sys.path.insert(0, os.path.abspath('../..'))

project = 'Tangl'
copyright = '2025, Derek Merck'
author = 'Derek Merck'
release = '3.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # for Google or NumPy style docstrings
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


import commonmark

# Note: to get :class:`foo` to work, you have to escape the ticks
#       i.e., :class:\`foo\' works
def docstring(app, what, name, obj, options, lines):
    md  = '\n'.join(lines)
    ast = commonmark.Parser().parse(md)
    rst = commonmark.ReStructuredTextRenderer().render(ast)
    lines.clear()
    lines += rst.splitlines()

    # if md.find(":class:"):
    #     print( rst )

def setup(app):
    app.connect('autodoc-process-docstring', docstring)

autodoc_typehints_description_target = "documented"
