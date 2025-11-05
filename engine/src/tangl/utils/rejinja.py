import logging

import jinja2

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class RecursiveTemplate(jinja2.Template):
    """Must instantiate with env.from_str(source, globals={}) if including globals"""

    def __init__(self, source, **kwargs):
        # Track the template source string
        self.source = source
        super().__init__(source=source, **kwargs)

    def render(self, *args, **kwargs) -> str:
        # recursive jinja2 evaluation
        s = super().render(*args, **kwargs)
        logger.debug( s )
        if "{{" in s or "{%" in s:
            templ = self.environment.from_string(s,
                                                 globals=self.globals,
                                                 template_class=self.__class__)
            return templ.render(*args, **kwargs)
        s = s.strip()
        return s


# try:
#     HAS_BOX = True
#     from box import Box
# except ImportError:
#     HAS_BOX = False
#     Box = dict
#
# class DereferencingTemplate(RecursiveTemplate):
#
#     def __init__(self, *args, **kwargs):
#         if not HAS_BOX:
#             raise ImportError("Install Box to use the DereferencingTemplate renderer.")
#         super().__init__(*args, **kwargs)
#
#     def render(self, *args, merge_keys: dict[str, str] = None, **kwargs) -> str:
#         merge_keys = merge_keys or {}
#         reference_vars = Box(self.globals, box_dots=True)
#         local_vars = Box()
#
#         for k, v in merge_keys.items():
#             value = reference_vars[k]
#             if v is None:
#                 local_vars.merge_update(value)
#                 reference_vars.merge_update(value)
#             else:
#                 local_vars[v] = value
#                 reference_vars[v] = value
#
#         local_vars.merge_update(kwargs)
#
#         s = super().render(*args, **local_vars)
#         return s
