from __future__ import annotations

from fnmatch import fnmatch
import re
from typing import Any


_BRACE_RE = re.compile(r"\{([^{}]+)\}")


def _expand_braces(pattern: str) -> list[str]:
    match = _BRACE_RE.search(pattern)
    if match is None:
        return [pattern]

    prefix = pattern[: match.start()]
    suffix = pattern[match.end() :]
    options = [opt.strip() for opt in match.group(1).split(",")]

    expanded: list[str] = []
    for option in options:
        for tail in _expand_braces(suffix):
            expanded.append(f"{prefix}{option}{tail}")
    return expanded


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

    for expanded in _expand_braces(template_scope):
        if _admitted_single(expanded, ctx_parts):
            return True
    return False


def _admitted_single(expanded_scope: str, ctx_parts: list[str]) -> bool:
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


def resolve_target_path(
    *,
    identifier: str | None,
    request_ctx: str | None,
    authored_path: str | None = None,
    is_qualified: bool = False,
) -> str | None:
    if not isinstance(identifier, str) or not identifier:
        return None

    if "." in identifier:
        return identifier

    if is_qualified and authored_path:
        # Backward-compatibility fallback when callers mark qualified without
        # providing a canonical identifier at compile time.
        if request_ctx:
            return f"{request_ctx}.{identifier}"
        return identifier

    if request_ctx:
        return f"{request_ctx}.{identifier}"
    return identifier


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
        except Exception:
            return False

    label = getattr(candidate, "label", None)
    return label == segment
