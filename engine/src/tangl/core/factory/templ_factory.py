# tangl/core/factory/templ_factory.py
from __future__ import annotations
from tangl.core.registry import Registry
from .template import Template, ET
from .hierarchical_template import HierarchicalTemplate

class TemplateFactory(Registry[Template]):
    """
    Registry of templates with materialization support.

    Examples:
        >>> # Create factory from root template
        >>> factory = TemplateFactory.from_root_templ(root_script)
        >>>
        >>> # Find templates
        >>> start_block = factory.find_one(
        ...     has_path="scene1.start",
        ...     has_tags="start"
        ... )
        >>>
        >>> # Materialize entity
        >>> node = TemplateFactory.materialize_templ(start_block)
    """

    @classmethod
    def from_root_templ(cls, root_templ: HierarchicalTemplate) -> TemplateFactory:
        """
        Create factory by flattening hierarchical template.

        Each registered template retains its hierarchical `path` and the derived
        scope metadata is tested by `get_selection_criteria()` when matched
        against a selector.

        Args:
            root_templ: Root of template hierarchy

        Returns:
            TemplateFactory with all templates registered
        """
        factory = cls(label=f"{root_templ.get_label()}_factory")

        # Visit entire tree and register
        for templ in root_templ.visit():
            factory.add(templ)

        return factory

    # todo: this redundant until it holds materialize dispatch
    @classmethod
    def materialize_templ(cls, templ: Template[ET], **kwargs) -> ET:
        """
        Create entity from template.

        Args:
            templ: Template to materialize
            kwargs: attrib overrides to be passed into instantiation

        Returns:
            Entity instance

        Note:
            This creates only the single entity - does NOT materialize
            children for graph items.
        """
        # Future -- use factory dispatch and provide hooks
        # factory.dispatch.do_materialize(self, ctx=params)
        # - calls: do_get_cls, do_materialize, do_init
        return templ.materialize(**kwargs)

    def all_paths(self) -> list[str]:
        return list(x.path for x in self.data.values())
