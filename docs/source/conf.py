import sys
import os
sys.path.insert(0, os.path.abspath('../../engine/src'))

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
    'myst_parser',
]

# extensions += [
#     "sphinx.ext.autosectionlabel",
#     "sphinx_copybutton",
#     "sphinx_design",            # cards/tabs/grids
#     "sphinxext.opengraph",      # social cards
#     # "sphinx_sitemap",         # if html_baseurl is set
#     # "sphinxcontrib.mermaid",  # sequence/flow diagrams
# ]
# html_baseurl = "https://<your-docs-domain>/"   # needed for sitemap & OpenGraph

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    # Add other projects here, such as:
    # 'requests': ('https://requests.readthedocs.io/en/latest/', None),
}

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# useful MyST extras
myst_enable_extensions = [
    "colon_fence",   # ::: fenced blocks
    "deflist",       # definition lists
    "linkify",       # autolink URLs
    # "smartquotes",   # typography
]

templates_path = ['_templates']
exclude_patterns = []

add_module_names = False
autodoc_typehints = 'none'
autodoc_typehints_description_target = "documented"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
# html_logo = "_static/logo-light.svg"
# html_favicon = "_static/favicon.png"
html_theme_options = {
    # "light_logo": "logo-light.svg",
    # "dark_logo": "logo-dark.svg",
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "top_of_page_button": "edit",  # or "back-to-top"
}
pygments_style = "tango"
pygments_dark_style = "native"

# html_theme = 'alabaster'
html_static_path = ['_static']

# Pydantic autodoc sigs
# extensions += ["autodoc_pydantic"]
# autodoc_pydantic_model_signature = False

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

def _is_doc_private_field(obj) -> bool:
    field = getattr(obj, "field_info", None) or getattr(obj, "model_field", None)
    if field is None:
        return False
    extra = getattr(field, "json_schema_extra", None) or {}
    return extra.get("doc_private") is True

def autodoc_skip_member(app, what, name, obj, skip, options):
    if _is_doc_private_field(obj):
        return True
    if name.startswith("_") and not name.startswith("__"):
        return True
    return None

def setup(app):
    app.connect("autodoc-skip-member", autodoc_skip_member)
    # app.connect('autodoc-process-docstring', docstring)
