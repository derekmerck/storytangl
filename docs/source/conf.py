import sys
import os
sys.path.insert(0, os.path.abspath('../../engine'))

project = 'StoryTangl'
copyright = '2025, Derek Merck'
author = 'Derek Merck'
release = '3.7'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # for Google or NumPy style docstrings
    'sphinx.ext.viewcode',
    'sphinx_markdown_builder',
    'sphinx.ext.intersphinx',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    # Add other projects here, such as:
    # 'requests': ('https://requests.readthedocs.io/en/latest/', None),
}

templates_path = ['_templates']
exclude_patterns = []

add_module_names = False
autodoc_typehints = 'none'
autodoc_typehints_description_target = "documented"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


# For markdown/myst docstrings
# import commonmark

# Note: to get :class:`foo` to work, you have to escape the ticks
#       i.e., :class:\`foo\' works
# def docstring(app, what, name, obj, options, lines):
#     md  = '\n'.join(lines)
#     ast = commonmark.Parser().parse(md)
#     rst = commonmark.ReStructuredTextRenderer().render(ast)
#     lines.clear()
#     lines += rst.splitlines()
#
#     # if md.find(":class:"):
#     #     print( rst )
#
# def setup(app):
#     app.connect('autodoc-process-docstring', docstring)

