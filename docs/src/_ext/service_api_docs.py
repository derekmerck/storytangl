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
from tangl.service.api_endpoint import ApiEndpoint, EndpointPolicy, ResourceBinding
from tangl.service.bootstrap import DEFAULT_ENDPOINT_POLICIES
from tangl.service.controllers import get_default_controllers
from tangl.service.operations import ServiceOperation, endpoint_for_operation


@dataclass(frozen=True)
class _ServiceEndpointDoc:
    """Resolved documentation fields for one controller endpoint."""

    controller: type
    endpoint_name: str
    endpoint: ApiEndpoint
    operation: ServiceOperation | None
    policy: EndpointPolicy

    @property
    def qualified_name(self) -> str:
        return f"{self.controller.__name__}.{self.endpoint_name}"

    @property
    def method_ref(self) -> str:
        return f"{self.endpoint.func.__module__}.{self.controller.__name__}.{self.endpoint_name}"


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


def _format_bindings(bindings: tuple[ResourceBinding, ...] | None) -> str:
    if bindings is None:
        return "inferred from type hints"
    if not bindings:
        return "none"
    return ", ".join(f"``{binding.value}``" for binding in bindings)


def _format_paths(paths: tuple[str, ...]) -> str:
    if not paths:
        return "none"
    return ", ".join(f"``{path}``" for path in paths)


def _operation_by_endpoint() -> dict[str, ServiceOperation]:
    return {
        endpoint_for_operation(operation): operation
        for operation in ServiceOperation
    }


def _effective_policy(endpoint_name: str, endpoint: ApiEndpoint) -> EndpointPolicy:
    policy = EndpointPolicy.from_endpoint(endpoint)
    override = DEFAULT_ENDPOINT_POLICIES.get(endpoint_name)
    if override is None:
        return policy
    return policy.merged(EndpointPolicy(**override))


def _endpoint_source_line(endpoint: ApiEndpoint) -> int:
    try:
        _, lineno = inspect.getsourcelines(endpoint.func)
    except (OSError, TypeError):  # pragma: no cover - doc ordering fallback
        return 0
    return lineno


def _service_endpoint_docs() -> list[_ServiceEndpointDoc]:
    operation_lookup = _operation_by_endpoint()
    docs: list[_ServiceEndpointDoc] = []
    for controller in get_default_controllers():
        endpoints = controller.get_api_endpoints()
        ordered = sorted(
            endpoints.items(),
            key=lambda item: _endpoint_source_line(item[1]),
        )
        for endpoint_name, endpoint in ordered:
            qualified_name = f"{controller.__name__}.{endpoint_name}"
            docs.append(
                _ServiceEndpointDoc(
                    controller=controller,
                    endpoint_name=endpoint_name,
                    endpoint=endpoint,
                    operation=operation_lookup.get(qualified_name),
                    policy=_effective_policy(qualified_name, endpoint),
                )
            )
    return docs


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


class ServiceOperationCatalogDirective(_GeneratedRstDirective):
    """Render a service endpoint catalog from live controller metadata."""

    def run(self) -> list[nodes.Node]:
        lines: list[str] = []
        docs = _service_endpoint_docs()

        current_controller: type | None = None
        for entry in docs:
            if entry.controller is not current_controller:
                current_controller = entry.controller
                if lines:
                    lines.append("")
                title = current_controller.__name__
                lines.extend(
                    [
                        title,
                        "-" * len(title),
                        "",
                    ]
                )

            label = f"``{entry.qualified_name}``"
            if entry.operation is not None:
                label = f"``{entry.operation.value}`` / {label}"

            lines.extend(
                [
                    label,
                    "",
                    f"  {_first_sentence(entry.endpoint.func)}",
                    "",
                    f"  :Controller endpoint: :meth:`{entry.method_ref}`",
                    (
                        f"  :Service operation token: ``{entry.operation.value}``"
                        if entry.operation is not None
                        else "  :Service operation token: not assigned (endpoint-only)"
                    ),
                    f"  :Endpoint group: ``{entry.endpoint.group}``",
                    (
                        "  :Method type: "
                        f"``{entry.endpoint.method_type.value}`` "
                        f"(default HTTP verb ``{entry.endpoint.method_type.http_verb()}``)"
                    ),
                    f"  :Response type: ``{entry.endpoint.response_type.value}``",
                    f"  :Access level: ``{entry.endpoint.access_level.name}``",
                    f"  :Hydration bindings: {_format_bindings(entry.endpoint.binds)}",
                    f"  :Writeback mode: ``{entry.policy.writeback_mode.value}``",
                    f"  :Persist paths: {_format_paths(entry.policy.persist_paths)}",
                    f"  :Call signature: ``{_format_signature(entry.endpoint.func)}``",
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

    app.add_directive("service-operation-catalog", ServiceOperationCatalogDirective)
    app.add_directive("rest-route-catalog", RestRouteCatalogDirective)
    return {
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
