from __future__ import annotations

"""Sphinx helpers for service- and REST-facing API inventory pages."""

from dataclasses import dataclass
import inspect
import re
from typing import Any

from docutils import nodes
from docutils.statemachine import StringList
from fastapi.routing import APIRoute
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from tangl.rest.api_server import app as api_server_app
from tangl.service import ServiceManager
from tangl.service.service_method import ServiceMethodSpec


@dataclass(frozen=True)
class _ServiceMethodDoc:
    """Resolved documentation fields for one canonical service method."""

    method_name: str
    method: Any
    spec: ServiceMethodSpec

    @property
    def qualified_name(self) -> str:
        return f"{ServiceManager.__name__}.{self.method_name}"

    @property
    def method_ref(self) -> str:
        return f"{self.method.__module__}.{ServiceManager.__name__}.{self.method_name}"


@dataclass(frozen=True)
class _RestRouteDoc:
    """Resolved documentation fields for one FastAPI route."""

    methods: tuple[str, ...]
    path: str
    handler_module: str
    handler_name: str
    summary: str
    tags: tuple[str, ...]
    operation_id: str

    @property
    def handler_ref(self) -> str:
        return f"{self.handler_module}.{self.handler_name}"


def _first_sentence(func: Any) -> str:
    doc = inspect.getdoc(func) or ""
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped:
            return re.sub(r":[a-zA-Z0-9_]+:`([^`]+)`", r"\1", stripped)
    return "No summary available."


def _format_annotation(value: Any) -> str:
    if value is inspect.Signature.empty:
        return ""
    if isinstance(value, str):
        return value
    try:
        return inspect.formatannotation(value)
    except Exception:  # pragma: no cover - defensive stringification for docs only
        if hasattr(value, "__name__"):
            return str(getattr(value, "__name__"))
        return repr(value)


def _format_signature(func: Any) -> str:
    signature = inspect.signature(func)
    params = list(signature.parameters.values())
    if params and params[0].name in {"self", "cls"}:
        params = params[1:]

    rendered_params = ", ".join(str(param) for param in params)
    rendered = f"({rendered_params})"

    return_annotation = _format_annotation(signature.return_annotation)
    if return_annotation:
        rendered = f"{rendered} -> {return_annotation}"
    return rendered


def _source_line(func: Any) -> int:
    try:
        _, lineno = inspect.getsourcelines(func)
    except (OSError, TypeError):  # pragma: no cover - doc ordering fallback
        return 0
    return lineno


def _service_method_docs() -> list[_ServiceMethodDoc]:
    docs: list[_ServiceMethodDoc] = []
    for method_name, spec in ServiceManager.get_service_methods().items():
        method = getattr(ServiceManager, method_name)
        docs.append(
            _ServiceMethodDoc(
                method_name=method_name,
                method=method,
                spec=spec,
            )
        )
    return sorted(docs, key=lambda item: _source_line(item.method))


def _rest_route_docs() -> list[_RestRouteDoc]:
    docs: list[_RestRouteDoc] = []
    for route in api_server_app.routes:
        if not isinstance(route, APIRoute):
            continue

        methods = tuple(
            sorted(
                method
                for method in route.methods
                if method not in {"HEAD", "OPTIONS"}
            )
        )
        docs.append(
            _RestRouteDoc(
                methods=methods,
                path=route.path,
                handler_module=route.endpoint.__module__,
                handler_name=route.endpoint.__name__,
                summary=_first_sentence(route.endpoint),
                tags=tuple(route.tags or ()),
                operation_id=route.operation_id or route.name,
            )
        )

    return sorted(docs, key=lambda item: (item.path, item.methods, item.handler_ref))


class _GeneratedRstDirective(SphinxDirective):
    """Base helper that renders generated reStructuredText."""

    has_content = False

    def _render_rst(self, lines: list[str]) -> list[nodes.Node]:
        content = StringList()
        source = self.get_source_info()[0] or self.env.docname
        for line in lines:
            content.append(line, source)

        container = nodes.container()
        container.document = self.state.document
        nested_parse_with_titles(self.state, content, container)
        return container.children


class ServiceMethodCatalogDirective(_GeneratedRstDirective):
    """Render a canonical service-method catalog from live manager metadata."""

    def run(self) -> list[nodes.Node]:
        lines: list[str] = []
        docs = _service_method_docs()

        title = ServiceManager.__name__
        lines.extend(
            [
                title,
                "-" * len(title),
                "",
            ]
        )

        for entry in docs:
            label = f"``{entry.method_name}``"
            if entry.spec.operation_id is not None:
                label = f"``{entry.spec.operation_id}`` / {label}"

            lines.extend(
                [
                    label,
                    "",
                    f"  {_first_sentence(entry.method)}",
                    "",
                    f"  :Service method: :meth:`{entry.method_ref}`",
                    (
                        f"  :Operation id: ``{entry.spec.operation_id}``"
                        if entry.spec.operation_id is not None
                        else "  :Operation id: not assigned"
                    ),
                    f"  :Access level: ``{entry.spec.access.value}``",
                    f"  :Context: ``{entry.spec.context.value}``",
                    f"  :Writeback: ``{entry.spec.writeback.value}``",
                    f"  :Blocking: ``{entry.spec.blocking.value}``",
                    (
                        f"  :Capability: ``{entry.spec.capability}``"
                        if entry.spec.capability is not None
                        else "  :Capability: none"
                    ),
                    f"  :Call signature: ``{_format_signature(entry.method)}``",
                    "",
                ]
            )

        return self._render_rst(lines)


class RestRouteCatalogDirective(_GeneratedRstDirective):
    """Render a REST route catalog from the mounted FastAPI app."""

    def run(self) -> list[nodes.Node]:
        lines: list[str] = []
        for route in _rest_route_docs():
            method_label = ", ".join(f"``{method}``" for method in route.methods)
            route_label = f"{method_label} ``{route.path}``"
            tags = ", ".join(f"``{tag}``" for tag in route.tags) or "none"
            lines.extend(
                [
                    route_label,
                    "",
                    f"  {route.summary}",
                    "",
                    f"  :Handler: ``{route.handler_ref}``",
                    f"  :Tags: {tags}",
                    f"  :Operation id: ``{route.operation_id}``",
                    "",
                ]
            )

        return self._render_rst(lines)


def setup(app) -> dict[str, bool]:
    """Register custom directives used by the StoryTangl API docs."""

    app.add_directive("service-method-catalog", ServiceMethodCatalogDirective)
    app.add_directive("rest-route-catalog", RestRouteCatalogDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
