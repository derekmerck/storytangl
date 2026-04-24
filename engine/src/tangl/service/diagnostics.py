"""Normalize authoring diagnostics for service and REST surfaces."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from tangl.story.fabula.types import AuthoredRef, CompileIssue, InitReport, UnresolvedDependency
from tangl.vm.provision.preview import Blocker

from .response import AuthoringDiagnostic, JsonValue


def _json_safe(value: Any) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, UUID):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [_json_safe(item) for item in value]
    return str(value)


def _source_from_authored_ref(source_ref: AuthoredRef | None) -> dict[str, JsonValue] | None:
    if source_ref is None:
        return None
    source = {
        key: value
        for key, value in asdict(source_ref).items()
        if value is not None
    }
    return source or None


def diagnostics_from_codec_state(
    codec_state: Mapping[str, Any] | None,
) -> list[AuthoringDiagnostic]:
    """Convert persisted codec loss records into decode diagnostics."""

    if not codec_state:
        return []
    records = codec_state.get("loss_records")
    if not isinstance(records, list):
        return []

    diagnostics: list[AuthoringDiagnostic] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        kind = str(record.get("kind") or "loss")
        feature = str(record.get("feature") or "unknown")
        passage = record.get("passage")
        excerpt = record.get("excerpt")
        note = record.get("note")
        source = {
            key: value
            for key, value in {
                "passage": _json_safe(passage),
                "excerpt": _json_safe(excerpt),
            }.items()
            if value is not None
        }
        details = {
            key: value
            for key, value in {
                "kind": _json_safe(kind),
                "feature": _json_safe(feature),
                "note": _json_safe(note),
            }.items()
            if value is not None
        }
        diagnostics.append(
            AuthoringDiagnostic(
                phase="decode",
                severity="warning",
                code=f"decode:{kind}:{feature}",
                message=f"Codec recorded {kind.replace('_', ' ')} for {feature!r}.",
                source=source or None,
                subject_label=str(passage) if passage is not None else None,
                details=details,
            )
        )
    return diagnostics


def diagnostics_from_compile_issues(issues: Iterable[CompileIssue]) -> list[AuthoringDiagnostic]:
    """Convert compiler diagnostics into the service report shape."""

    diagnostics: list[AuthoringDiagnostic] = []
    for issue in issues:
        details = dict(issue.details)
        if issue.related_identifiers:
            details.setdefault("related_identifiers", list(issue.related_identifiers))
        diagnostics.append(
            AuthoringDiagnostic(
                phase=issue.phase,
                severity=issue.severity.value,
                code=issue.code,
                message=issue.message,
                source=_source_from_authored_ref(issue.source_ref),
                subject_label=issue.subject_label,
                details=_json_safe(details),
            )
        )
    return diagnostics


def diagnostics_from_init_report(report: InitReport) -> list[AuthoringDiagnostic]:
    """Convert story initialization diagnostics without changing runtime types."""

    diagnostics: list[AuthoringDiagnostic] = []
    for warning in report.warnings:
        diagnostics.append(
            AuthoringDiagnostic(
                phase="runtime",
                severity="warning",
                code="runtime:init_warning",
                message=warning,
            )
        )
    for dependency in report.unresolved_hard:
        diagnostics.append(_diagnostic_from_dependency(dependency, severity="error"))
    for dependency in report.unresolved_soft:
        diagnostics.append(_diagnostic_from_dependency(dependency, severity="warning"))
    return diagnostics


def diagnostic_from_runtime_blocker(blocker: Blocker) -> AuthoringDiagnostic:
    """Convert a provisioning blocker into the common diagnostics shape."""

    return AuthoringDiagnostic(
        phase="runtime",
        severity="warning",
        code=f"runtime:blocker:{blocker.reason}",
        message=blocker.reason.replace("_", " "),
        details=_json_safe(blocker.context),
    )


def _diagnostic_from_dependency(
    dependency: UnresolvedDependency,
    *,
    severity: Literal["error", "warning"],
) -> AuthoringDiagnostic:
    return AuthoringDiagnostic(
        phase="runtime",
        severity=severity,
        code="runtime:unresolved_dependency",
        message="Story initialization could not resolve a required dependency.",
        subject_label=dependency.label,
        details=_json_safe(
            {
                "dependency_id": dependency.dependency_id,
                "source_id": dependency.source_id,
                "identifier": dependency.identifier,
                "hard_requirement": dependency.hard_requirement,
            }
        ),
    )
