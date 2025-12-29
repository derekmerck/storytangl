# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Module search path
import sys
from pathlib import Path

here = Path(__file__).absolute().parent
sys.path.insert(0, str(here.parent))
sys.path.insert(0, str(here/'extensions'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'StoryTangl'
copyright = '2023, TanglDev'
author = 'TanglDev'
release = '2.5'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    'sphinx.ext.autodoc.typehints',
    "sphinxcontrib.openapi",
]
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'working', '_static']

autodoc_typehints = "description"
autodoc_typehints_format = "short"
autodoc_member_order = "bysource"
add_module_names = False

autodoc_default_options = {
    'member-order': 'bysource',
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'exclude-members': 'guid, uid, locals, meta, parent',
    'special-members': '__on_init_world__, __on_init_story__, __on_init_node__, __on_render_node__, __on_get_node_media__, __on_get_story_status__, __on_get_ns__'
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "pydata_sphinx_theme"
html_context = {
   "default_mode": "dark"
}
# html_theme = 'alabaster'
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
