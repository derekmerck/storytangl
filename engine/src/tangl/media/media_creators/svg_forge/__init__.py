__version__ = "3.2.0"
__title__ = "VectorForge"

from .vector_forge import VectorForge
from .vector_spec import VectorSpec, VectorScriptItem
from .svg_catalog import (
    SvgCatalog, SvgCatalogDiagnostic, SvgCatalogEntry, SvgGroupDeclaration, index_svg_catalog,
)
from .svg_plan import Operation, Recipe, RenderPlan, Rule, resolve_plan
