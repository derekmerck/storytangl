from __future__ import annotations

from fnmatch import fnmatch
import re
from typing import Any


_BRACE_RE = re.compile(r"\{([^{}]+)\}")
MAX_SCOPE_BRACE_EXPANSIONS = 256


class _ScopeExpansionLimitError(ValueError):
    """Raised when scope brace expansion exceeds configured limit."""


def _expand_braces(
    pattern: str,
    *,
    max_expansions: int = MAX_SCOPE_BRACE_EXPANSIONS,
) -> list[str]:
    remaining = max_expansions

    def _expand(value: str) -> list[str]:
        nonlocal remaining
        match = _BRACE_RE.search(value)
        if match is None:
            if remaining <= 0:
                raise _ScopeExpansionLimitError(
                    "scope brace expansion exceeds maximum allowed combinations"
                )
            remaining -= 1
            return [value]

        prefix = value[: match.start()]
        suffix = value[match.end() :]
        options = [opt.strip() for opt in match.group(1).split(",")]

        expanded: list[str] = []
        for option in options:
            for tail in _expand(suffix):
                expanded.append(f"{prefix}{option}{tail}")
        return expanded

    return _expand(pattern)


def split_path(path: str | None) -> list[str]:
    if not isinstance(path, str) or not path:
        return []
    return [segment for segment in path.split(".") if segment]


def scope_prefix(scope: str | None) -> list[str]:
    if scope in (None, "", "*"):
        return []
    parts = split_path(scope)
    while parts and parts[-1] in ("*", "**"):
        parts.pop()
    return parts


def context_prefix(resolved_path: str | None) -> list[str]:
    parts = split_path(resolved_path)
    return parts[:-1] if len(parts) > 1 else []


def admitted(template_scope: str | None, target_ctx: str | None) -> bool:
    if template_scope in (None, "", "*"):
        return True
    if not isinstance(target_ctx, str) or not target_ctx:
        return False

    ctx_parts = split_path(target_ctx)
    if not ctx_parts:
        return False

    try:
        expanded_scopes = _expand_braces(template_scope)
    except _ScopeExpansionLimitError:
        # Fail closed for pathological expansion inputs.
        return False

    for expanded in expanded_scopes:
        if _admitted_single(expanded, ctx_parts):
            return True
    return False


def _admitted_single(expanded_scope: str, ctx_parts: list[str]) -> bool:
    """Match scope prefix against a placement context with an implicit leaf.

    ``template_scope`` describes where a template may be placed, not the final
    full path itself. The context therefore must include one additional trailing
    segment: ``a.b`` admits ``a.b.c`` but not ``a.b``.
    """
    scope_parts = split_path(expanded_scope)
    if not scope_parts:
        return True

    if scope_parts[-1] in ("*", "**"):
        prefix = scope_parts[:-1]
    else:
        prefix = scope_parts

    # Scope always predicates a placement context containing a leaf segment.
    if len(ctx_parts) <= len(prefix):
        return False

    # Intentionally compare only the prefix segment-by-segment: len(ctx_parts) >
    # len(prefix) above guarantees extra ctx_parts are valid trailing depth, so
    # zip(prefix, ctx_parts) with fnmatch checks only required prefix positions.
    for expected, actual in zip(prefix, ctx_parts):
        if not fnmatch(actual, expected):
            return False
    return True


def levenshtein_components(a: list[str], b: list[str]) -> int:
    n = len(a)
    m = len(b)
    if n == 0:
        return m
    if m == 0:
        return n

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if fnmatch(b[j - 1], a[i - 1]) else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
    return dp[n][m]


def scope_distance(template_scope: str | None, target_ctx: str | None) -> int:
    if template_scope in (None, "", "*"):
        return 0
    return levenshtein_components(
        scope_prefix(template_scope),
        context_prefix(target_ctx),
    )


def is_qualified_path(path: str | None) -> bool:
    return isinstance(path, str) and "." in path


def leaf_identifier(identifier: str | None) -> str | None:
    parts = split_path(identifier)
    if not parts:
        return None
    return parts[-1]


def target_context_candidates(
    *,
    identifier: str | None,
    request_ctx: str | None,
    authored_path: str | None = None,
    is_qualified: bool = False,
    is_absolute: bool = False,
) -> list[str]:
    # authored_path/is_qualified are kept in the signature for call-site symmetry
    # with resolve_target_path and future policy forks.
    _ = authored_path
    _ = is_qualified

    if not isinstance(identifier, str) or not identifier:
        return []

    if "." in identifier:
        return [identifier]

    if is_absolute:
        return [identifier]

    candidates: list[str] = []
    seen: set[str] = set()

    request_parts = split_path(request_ctx)
    for index in range(len(request_parts), 0, -1):
        prefix = ".".join(request_parts[:index])
        candidate = f"{prefix}.{identifier}"
        if candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)

    if identifier not in seen:
        candidates.append(identifier)
    return candidates


def resolve_target_path(
    *,
    identifier: str | None,
    request_ctx: str | None,
    authored_path: str | None = None,
    is_qualified: bool = False,
    is_absolute: bool = False,
) -> str | None:
    candidates = target_context_candidates(
        identifier=identifier,
        request_ctx=request_ctx,
        authored_path=authored_path,
        is_qualified=is_qualified,
        is_absolute=is_absolute,
    )
    if not candidates:
        return None
    return candidates[0]


def build_plan(target_ctx: str | None, graph: Any) -> list[str]:
    segments = split_path(target_ctx)
    if len(segments) <= 1:
        return []

    prefix = segments[:-1]
    if graph is None:
        return list(prefix)

    plan: list[str] = []
    current: Any | None = None

    for index, segment in enumerate(prefix):
        if index == 0:
            next_node = _find_top_level(graph, segment)
        elif current is None:
            next_node = None
        else:
            next_node = _find_child(current, segment)

        if next_node is None:
            plan.extend(prefix[index:])
            break
        current = next_node

    return plan


def prefix_paths(path: str | None) -> list[str]:
    segments = split_path(path)
    if not segments:
        return []
    return [".".join(segments[: idx + 1]) for idx in range(len(segments))]


def _find_top_level(graph: Any, segment: str) -> Any | None:
    values = getattr(graph, "values", None)
    if not callable(values):
        return None

    for candidate in values():
        if getattr(candidate, "parent", None) is not None:
            continue
        if _matches_segment(candidate, segment):
            return candidate
    return None


def _find_child(parent: Any, segment: str) -> Any | None:
    children = getattr(parent, "children", None)
    if callable(children):
        for candidate in children():
            if _matches_segment(candidate, segment):
                return candidate
        return None

    members = getattr(parent, "members", None)
    if callable(members):
        for candidate in members():
            if _matches_segment(candidate, segment):
                return candidate
        return None
    return None


def _matches_segment(candidate: Any, segment: str) -> bool:
    has_identifier = getattr(candidate, "has_identifier", None)
    if callable(has_identifier):
        try:
            return bool(has_identifier(segment))
        except (TypeError, ValueError, AttributeError):
            return False

    label = getattr(candidate, "label", None)
    return label == segment
