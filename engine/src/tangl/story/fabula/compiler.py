from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

from tangl.core import Entity, EntityTemplate, Selector, TemplateRegistry
from tangl.core.template import TemplateGroup
from tangl.ir.story_ir import StoryScript
from tangl.vm import TraversableNode

from ..concepts import Actor, Location
from ..episode import Action, Block, MenuBlock, Scene
from .types import AuthoredRef, CompileIssue, CompileSeverity, JsonValue


ISSUE_DUPLICATE_LABEL = "compile:duplicate_label"
ISSUE_DANGLING_SUCCESSOR_REF = "compile:dangling_successor_ref"
ISSUE_DANGLING_ACTOR_REF = "compile:dangling_actor_ref"
ISSUE_DANGLING_LOCATION_REF = "compile:dangling_location_ref"
ISSUE_EMPTY_ENTRY_RESOLUTION = "compile:empty_entry_resolution"

# Allowed ``details`` keys per issue code. Keep this close to the compiler
# helpers so the JSON-like payload shape stays explicit and testable.
_COMPILE_ISSUE_DETAIL_KEYS: dict[str, tuple[str, ...]] = {
    ISSUE_DUPLICATE_LABEL: ("normalized_label", "occurrences"),
    ISSUE_DANGLING_SUCCESSOR_REF: ("field", "authored_ref", "canonical_ref"),
    ISSUE_DANGLING_ACTOR_REF: ("reference_key", "missing_ref"),
    ISSUE_DANGLING_LOCATION_REF: ("reference_key", "missing_ref"),
    ISSUE_EMPTY_ENTRY_RESOLUTION: ("requested_entry_ids", "resolution_strategy"),
}


@dataclass(slots=True)
class _DeclaredTemplate:
    template_label: str
    payload_label: str | None
    payload_kind: type[Entity]
    source_ref: AuthoredRef | None


@dataclass(slots=True)
class _PendingDiagnostic:
    code: str
    subject_label: str | None
    source_ref: AuthoredRef | None
    related_identifiers: list[str] = field(default_factory=list)
    details: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(slots=True)
class _CompileCollector:
    """Compiler-internal declaration and reference tracker.

    This collector is intentionally ephemeral. It exists only during
    compilation so validation can reason about normalized labels before lookup
    behavior hides collisions. Only ``CompileIssue`` records persist on the
    returned bundle.
    """

    default_source_path: str | None = None
    default_story_key: str | None = None
    declarations: list[_DeclaredTemplate] = field(default_factory=list)
    declarations_by_template_label: dict[str, list[_DeclaredTemplate]] = field(default_factory=dict)
    pending: list[_PendingDiagnostic] = field(default_factory=list)

    @classmethod
    def from_source_map(cls, source_map: dict[str, Any] | None) -> "_CompileCollector":
        if not isinstance(source_map, dict):
            return cls()
        refs = source_map.get("__source_files__")
        if not isinstance(refs, list) or not refs:
            return cls()
        first = refs[0]
        if isinstance(first, dict):
            return cls(
                default_source_path=_coerce_text(first.get("path")),
                default_story_key=_coerce_text(first.get("story_key")),
            )
        return cls(
            default_source_path=_coerce_text(getattr(first, "path", None)),
            default_story_key=_coerce_text(getattr(first, "story_key", None)),
        )

    def build_source_ref(
        self,
        *,
        authored_path: str | None,
        label: str | None,
        note: str | None = None,
    ) -> AuthoredRef | None:
        source_ref = AuthoredRef(
            path=self.default_source_path,
            story_key=self.default_story_key,
            authored_path=authored_path,
            label=label,
            note=note,
        )
        if any(
            (
                source_ref.path,
                source_ref.story_key,
                source_ref.authored_path,
                source_ref.label,
                source_ref.note,
            )
        ):
            return source_ref
        return None

    def add_declaration(
        self,
        *,
        template_label: str,
        payload: Entity,
        authored_path: str,
    ) -> None:
        declared = _DeclaredTemplate(
            template_label=template_label,
            payload_label=_coerce_text(payload.get_label() if hasattr(payload, "get_label") else None),
            payload_kind=payload.__class__,
            source_ref=self.build_source_ref(
                authored_path=authored_path,
                label=template_label,
            ),
        )
        self.declarations.append(declared)
        self.declarations_by_template_label.setdefault(template_label, []).append(declared)

    def add_pending(
        self,
        *,
        code: str,
        subject_label: str | None,
        authored_path: str,
        related_identifiers: list[str] | None = None,
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        self.pending.append(
            _PendingDiagnostic(
                code=code,
                subject_label=subject_label,
                source_ref=self.build_source_ref(
                    authored_path=authored_path,
                    label=subject_label,
                ),
                related_identifiers=list(related_identifiers or []),
                details=_sanitize_issue_details(code, details or {}),
            )
        )

    def has_candidate(self, identifier: str, *, kind: type[Entity]) -> bool:
        for declaration in self.declarations:
            if not issubclass(declaration.payload_kind, kind):
                continue
            if identifier == declaration.template_label:
                return True
            if declaration.payload_label and identifier == declaration.payload_label:
                return True
        return False

    def build_issues(
        self,
        *,
        story_label: str,
        entry_template_ids: list[str],
        resolution_strategy: str,
    ) -> list[CompileIssue]:
        issues: list[CompileIssue] = []
        issues.extend(self._build_duplicate_issues())
        issues.extend(self._build_pending_issues())
        entry_issue = self._build_entry_issue(
            story_label=story_label,
            entry_template_ids=entry_template_ids,
            resolution_strategy=resolution_strategy,
        )
        if entry_issue is not None:
            issues.append(entry_issue)
        return sorted(issues, key=_compile_issue_sort_key)

    def _build_duplicate_issues(self) -> list[CompileIssue]:
        issues: list[CompileIssue] = []
        for template_label, declarations in self.declarations_by_template_label.items():
            if len(declarations) < 2:
                continue
            occurrences = [
                source_ref.authored_path
                for declaration in declarations
                if (source_ref := declaration.source_ref) is not None and source_ref.authored_path
            ]
            issue = CompileIssue(
                code=ISSUE_DUPLICATE_LABEL,
                severity=CompileSeverity.ERROR,
                message=(
                    f"Compile label {template_label!r} was declared more than once "
                    "in the compiled bundle namespace."
                ),
                subject_label=template_label,
                source_ref=declarations[0].source_ref,
                details=_sanitize_issue_details(
                    ISSUE_DUPLICATE_LABEL,
                    {
                    "normalized_label": template_label,
                    "occurrences": occurrences,
                    },
                ),
            )
            issues.append(issue)
        return issues

    def _build_pending_issues(self) -> list[CompileIssue]:
        issues: list[CompileIssue] = []
        for pending in self.pending:
            missing_identifier = next(iter(pending.related_identifiers), None)
            if missing_identifier is None:
                continue
            required_kind = _required_kind_for_issue_code(pending.code)
            if self.has_candidate(missing_identifier, kind=required_kind):
                continue
            issues.append(
                CompileIssue(
                    code=pending.code,
                    severity=CompileSeverity.ERROR,
                    message=_message_for_pending_issue(
                        code=pending.code,
                        subject_label=pending.subject_label,
                        identifier=missing_identifier,
                    ),
                    subject_label=pending.subject_label,
                    source_ref=pending.source_ref,
                    related_identifiers=list(pending.related_identifiers),
                    details=dict(pending.details),
                )
            )
        return issues

    def _build_entry_issue(
        self,
        *,
        story_label: str,
        entry_template_ids: list[str],
        resolution_strategy: str,
    ) -> CompileIssue | None:
        if entry_template_ids and any(
            self.has_candidate(identifier, kind=TraversableNode)
            for identifier in entry_template_ids
        ):
            return None

        authored_path = "metadata.start_at" if resolution_strategy == "metadata.start_at" else "metadata"
        return CompileIssue(
            code=ISSUE_EMPTY_ENTRY_RESOLUTION,
            severity=CompileSeverity.ERROR,
            message=(
                f"Story {story_label!r} resolved no usable entry templates during compile "
                "normalization."
            ),
            subject_label=story_label,
            source_ref=self.build_source_ref(
                authored_path=authored_path,
                label=story_label,
            ),
            details=_sanitize_issue_details(
                ISSUE_EMPTY_ENTRY_RESOLUTION,
                {
                    "requested_entry_ids": list(entry_template_ids),
                    "resolution_strategy": resolution_strategy,
                },
            ),
        )


def _compile_issue_sort_key(issue: CompileIssue) -> tuple[str, str, str, str, str]:
    source_ref = issue.source_ref
    return (
        _coerce_text(source_ref.path if source_ref is not None else None) or "",
        _coerce_text(source_ref.authored_path if source_ref is not None else None) or "",
        issue.subject_label or "",
        issue.code,
        issue.message,
    )


def _message_for_pending_issue(*, code: str, subject_label: str | None, identifier: str) -> str:
    subject = subject_label or "unknown"
    if code == ISSUE_DANGLING_SUCCESSOR_REF:
        return f"Successor reference {identifier!r} from {subject!r} does not resolve in this bundle."
    if code == ISSUE_DANGLING_ACTOR_REF:
        return f"Actor reference {identifier!r} from {subject!r} does not resolve in this bundle."
    if code == ISSUE_DANGLING_LOCATION_REF:
        return f"Location reference {identifier!r} from {subject!r} does not resolve in this bundle."
    return f"Compile diagnostic {code!r} for {subject!r} references {identifier!r}."


def _required_kind_for_issue_code(code: str) -> type[Entity]:
    if code == ISSUE_DANGLING_SUCCESSOR_REF:
        return TraversableNode
    if code == ISSUE_DANGLING_ACTOR_REF:
        return Actor
    if code == ISSUE_DANGLING_LOCATION_REF:
        return Location
    return Entity


def _sanitize_issue_details(code: str, details: dict[str, JsonValue]) -> dict[str, JsonValue]:
    allowed_keys = _COMPILE_ISSUE_DETAIL_KEYS.get(code)
    if not allowed_keys:
        return dict(details)
    return {key: details[key] for key in allowed_keys if key in details}


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


@dataclass(slots=True)
class StoryTemplateBundle:
    """StoryTemplateBundle()

    Canonical output of :class:`StoryCompiler`.

    Why
    ----
    Separating compilation from materialization lets one validated script bundle
    produce many independent story graphs without reparsing authored input.

    Key Features
    ------------
    * Carries the validated :class:`~tangl.core.TemplateRegistry` tree used by
      the materializer.
    * Preserves ``metadata``, story ``locals``, source mapping, and codec state
      alongside the template hierarchy.
    * Records ``entry_template_ids`` so materialization can resolve the graph's
      initial cursor positions deterministically.
    * Stores structured compiler diagnostics for cheap bundle-local integrity
      problems without forcing materialization first.

    API
    ---
    - :attr:`metadata` stores story-level metadata used by runtime setup.
    - :attr:`locals` stores authored top-level namespace values.
    - :attr:`template_registry` contains the validated template hierarchy.
    - :attr:`entry_template_ids` lists the template ids used for initial cursor
      resolution.
    - :attr:`issues` stores structured compile diagnostics for later inspection.
    - :attr:`source_map`, :attr:`codec_state`, and :attr:`codec_id` preserve
      compile-time provenance and codec context.
    """

    metadata: dict[str, Any]
    locals: dict[str, Any]
    template_registry: TemplateRegistry
    entry_template_ids: list[str]
    source_map: dict[str, Any]
    codec_state: dict[str, Any]
    codec_id: str | None
    issues: list[CompileIssue] = field(default_factory=list)


class StoryCompiler:
    """StoryCompiler()

    Validate and normalize authored story script data into a
    :class:`StoryTemplateBundle`.

    Why
    ----
    Authored story scripts are intentionally lightweight. The compiler turns
    that loose authoring shape into a typed, scoped template tree that runtime
    materialization and provisioning can trust.

    Key Features
    ------------
    * Accepts raw dicts or validated :class:`~tangl.ir.story_ir.StoryScript`
      instances.
    * Builds scene and block template hierarchy used by runtime scope matching.
    * Canonicalizes action references so authored shorthand and qualified
      references resolve into a stable form.
    * Attempts to resolve authored ``kind`` references during compilation when
      an override cannot be imported.

    API
    ---
    - :meth:`compile` is the supported public entry point.
    """

    @staticmethod
    def validate_ir(script_data: dict[str, Any]) -> StoryScript:
        """Validate raw script data against the near-native IR schema.

        Use this when authored near-native YAML should be linted explicitly.
        Compilation itself accepts runtime-ready dicts directly so codecs are
        not forced through the at-rest IR model.
        """
        return StoryScript.model_validate(script_data)

    def compile(
        self,
        script_data: dict[str, Any] | StoryScript,
        *,
        source_map: dict[str, Any] | None = None,
        codec_state: dict[str, Any] | None = None,
        codec_id: str | None = None,
    ) -> StoryTemplateBundle:
        """Compile authored story data into a reusable template bundle.

        Accepts raw script dictionaries or validated
        :class:`~tangl.ir.story_ir.StoryScript` objects.

        Raw dicts are compiled directly. Use :meth:`validate_ir` separately
        when authored near-native data should be linted against the IR schema.
        """
        if isinstance(script_data, StoryScript):
            data = script_data.model_dump(by_alias=True, exclude_none=True)
            label = script_data.label
        else:
            data = dict(script_data)
            label = str(data.get("label") or "story")

        metadata = dict(data.get("metadata") or {})
        locals_ns = dict(data.get("globals") or data.get("locals") or {})
        collector = _CompileCollector.from_source_map(source_map)

        registry = TemplateRegistry(label=f"{label}_templates")
        root = TemplateGroup(
            label=label,
            payload=Entity(label=label),
            registry=registry,
        )

        self._compile_section(
            parent=root,
            items=data.get("templates"),
            fallback_kind=TraversableNode,
            collector=collector,
            authored_path_prefix="templates",
        )
        self._compile_section(
            parent=root,
            items=data.get("actors"),
            fallback_kind=Actor,
            collector=collector,
            authored_path_prefix="actors",
        )
        self._compile_section(
            parent=root,
            items=data.get("locations"),
            fallback_kind=Location,
            collector=collector,
            authored_path_prefix="locations",
        )

        scenes = self._normalize_mapping(data.get("scenes"))
        root_scene_labels = {scene_label for scene_label, _ in scenes}
        for scene_label, scene_data in scenes:
            scene_authored_path = f"scenes.{scene_label}"
            scene_payload = self._build_payload(
                kind=self._resolve_kind(
                    scene_data.get("kind"),
                    fallback=Scene,
                ),
                payload={
                    **scene_data,
                    "label": scene_data.get("label") or scene_label,
                    "title": scene_data.get("title") or scene_data.get("text") or "",
                    "roles": self._normalize_list(scene_data.get("roles")),
                    "settings": self._normalize_list(scene_data.get("settings")),
                },
                default_label=scene_label,
            )
            collector.add_declaration(
                template_label=scene_label,
                payload=scene_payload,
                authored_path=scene_authored_path,
            )
            scene_templ = TemplateGroup(
                label=scene_label,
                payload=scene_payload,
                registry=registry,
            )
            root.add_child(scene_templ)
            self._collect_provider_ref_issues(
                collector=collector,
                specs=scene_payload.roles,
                source_label=scene_label,
                authored_path_prefix=f"{scene_authored_path}.roles",
                field_name="roles",
                issue_code=ISSUE_DANGLING_ACTOR_REF,
                reference_keys=("actor_ref", "actor_template_ref"),
            )
            self._collect_provider_ref_issues(
                collector=collector,
                specs=scene_payload.settings,
                source_label=scene_label,
                authored_path_prefix=f"{scene_authored_path}.settings",
                field_name="settings",
                issue_code=ISSUE_DANGLING_LOCATION_REF,
                reference_keys=("location_ref", "location_template_ref"),
            )

            self._compile_section(
                parent=scene_templ,
                items=scene_data.get("templates"),
                fallback_kind=TraversableNode,
                collector=collector,
                authored_path_prefix=f"{scene_authored_path}.templates",
            )

            blocks = self._normalize_mapping(scene_data.get("blocks"))
            for block_index, (block_label, block_data) in enumerate(blocks):
                block_authored_path = f"{scene_authored_path}.blocks.{block_label}"
                qualified_label = f"{scene_label}.{block_label}"
                actions = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("actions")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                continues = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("continues")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                redirects = self._canonicalize_action_specs(
                    self._normalize_list(block_data.get("redirects")),
                    scene_label=scene_label,
                    root_scene_labels=root_scene_labels,
                )
                next_qualified = self._next_block_label(blocks, block_index, scene_label)
                for spec_list in (actions, continues, redirects):
                    for spec in spec_list:
                        if not spec.get("successor_ref") and next_qualified is not None:
                            spec["successor_ref"] = next_qualified
                            spec["successor_is_absolute"] = False
                            spec["successor_is_inferred"] = True
                self._collect_successor_issues(
                    collector=collector,
                    specs=actions,
                    source_label=qualified_label,
                    authored_path_prefix=f"{block_authored_path}.actions",
                    field_name="actions",
                )
                self._collect_successor_issues(
                    collector=collector,
                    specs=continues,
                    source_label=qualified_label,
                    authored_path_prefix=f"{block_authored_path}.continues",
                    field_name="continues",
                )
                self._collect_successor_issues(
                    collector=collector,
                    specs=redirects,
                    source_label=qualified_label,
                    authored_path_prefix=f"{block_authored_path}.redirects",
                    field_name="redirects",
                )

                block_payload = self._build_payload(
                    kind=self._resolve_kind(
                        block_data.get("kind")
                        or block_data.get("block_cls"),
                        fallback=Block,
                    ),
                    payload={
                        **block_data,
                        "label": block_data.get("label") or block_label,
                        "actions": actions,
                        "continues": continues,
                        "redirects": redirects,
                        "roles": self._normalize_list(block_data.get("roles")),
                        "settings": self._normalize_list(block_data.get("settings")),
                        "media": self._normalize_list(block_data.get("media")),
                    },
                    default_label=block_label,
                )
                collector.add_declaration(
                    template_label=qualified_label,
                    payload=block_payload,
                    authored_path=block_authored_path,
                )
                block_templ = TemplateGroup(
                    label=qualified_label,
                    payload=block_payload,
                    registry=registry,
                )
                scene_templ.add_child(block_templ)
                self._collect_provider_ref_issues(
                    collector=collector,
                    specs=block_payload.roles,
                    source_label=qualified_label,
                    authored_path_prefix=f"{block_authored_path}.roles",
                    field_name="roles",
                    issue_code=ISSUE_DANGLING_ACTOR_REF,
                    reference_keys=("actor_ref", "actor_template_ref"),
                )
                self._collect_provider_ref_issues(
                    collector=collector,
                    specs=block_payload.settings,
                    source_label=qualified_label,
                    authored_path_prefix=f"{block_authored_path}.settings",
                    field_name="settings",
                    issue_code=ISSUE_DANGLING_LOCATION_REF,
                    reference_keys=("location_ref", "location_template_ref"),
                )

                self._compile_section(
                    parent=block_templ,
                    items=block_data.get("templates"),
                    fallback_kind=TraversableNode,
                    collector=collector,
                    authored_path_prefix=f"{block_authored_path}.templates",
                )

        entry_template_ids, resolution_strategy = self._resolve_entry_template_ids(
            metadata=metadata,
            registry=registry,
        )
        issues = collector.build_issues(
            story_label=label,
            entry_template_ids=entry_template_ids,
            resolution_strategy=resolution_strategy,
        )

        return StoryTemplateBundle(
            metadata=metadata,
            locals=locals_ns,
            template_registry=registry,
            entry_template_ids=entry_template_ids,
            issues=issues,
            source_map=source_map or {},
            codec_state=codec_state or {},
            codec_id=codec_id,
        )

    def _compile_section(
        self,
        *,
        parent: TemplateGroup,
        items: Any,
        fallback_kind: type[Entity],
        collector: _CompileCollector,
        authored_path_prefix: str,
    ) -> None:
        for label, item_data in self._normalize_mapping(items):
            parent_label = parent.get_label()
            scoped_label = (
                label
                if getattr(parent, "parent", None) is None
                else f"{parent_label}.{label}"
            )
            payload = self._build_payload(
                kind=self._resolve_kind(
                    item_data.get("kind"),
                    fallback=fallback_kind,
                ),
                payload={**item_data, "label": item_data.get("label") or label},
                default_label=label,
            )
            collector.add_declaration(
                template_label=scoped_label,
                payload=payload,
                authored_path=f"{authored_path_prefix}.{label}",
            )
            templ = TemplateGroup(
                label=scoped_label,
                payload=payload,
                registry=parent.registry,
            )
            parent.add_child(templ)
            self._compile_section(
                parent=templ,
                items=item_data.get("templates"),
                fallback_kind=fallback_kind,
                collector=collector,
                authored_path_prefix=f"{authored_path_prefix}.{label}.templates",
            )

    @staticmethod
    def _normalize_mapping(value: Any) -> list[tuple[str, dict[str, Any]]]:
        if not value:
            return []
        if isinstance(value, dict):
            items: list[tuple[str, dict[str, Any]]] = []
            for label, data in value.items():
                if isinstance(data, dict):
                    payload = dict(data)
                else:
                    payload = dict(getattr(data, "model_dump", lambda **_: {})())
                payload.setdefault("label", label)
                items.append((str(label), payload))
            return items
        items = []
        anon_counter = 0
        for item in value:
            if isinstance(item, dict):
                payload = dict(item)
            else:
                payload = dict(getattr(item, "model_dump", lambda **_: {})())
            label = payload.get("label")
            if not label:
                label = f"_anon_{anon_counter}"
                anon_counter += 1
                payload["label"] = label
                payload["_is_anonymous"] = True
            items.append((str(label), payload))
        return items

    @staticmethod
    def _normalize_list(value: Any) -> list[dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, dict):
            out: list[dict[str, Any]] = []
            for label, data in value.items():
                if isinstance(data, dict):
                    payload = dict(data)
                else:
                    payload = dict(getattr(data, "model_dump", lambda **_: {})())
                payload.setdefault("label", label)
                out.append(payload)
            return out
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(dict(item))
            else:
                out.append(dict(getattr(item, "model_dump", lambda **_: {})()))
        return out

    @staticmethod
    def _canonicalize_action_specs(
        specs: list[dict[str, Any]],
        *,
        scene_label: str,
        root_scene_labels: set[str],
    ) -> list[dict[str, Any]]:
        """Return canonical action specs for one scene.

        Part A policy: when a bare successor token collides with a root scene
        label, it is treated as an absolute scene destination by design.
        """
        normalized: list[dict[str, Any]] = []
        for spec in specs:
            payload = dict(spec)
            authored = payload.get("authored_successor_ref")
            if not (isinstance(authored, str) and authored):
                authored = payload.get("successor_ref")
                if authored is None:
                    authored = (
                        payload.get("successor")
                        or payload.get("next")
                        or payload.get("target_ref")
                        or payload.get("target_node")
                    )
                if isinstance(authored, str) and authored:
                    payload["authored_successor_ref"] = authored

            canonical = payload.get("successor_ref")
            if not (isinstance(canonical, str) and canonical):
                canonical = authored
            if isinstance(canonical, str) and canonical:
                if "." in canonical:
                    payload["successor_ref"] = canonical
                    payload["successor_is_absolute"] = False
                elif canonical in root_scene_labels:
                    payload["successor_ref"] = canonical
                    payload["successor_is_absolute"] = True
                else:
                    payload["successor_ref"] = f"{scene_label}.{canonical}"
                    payload["successor_is_absolute"] = False
            normalized.append(payload)
        return normalized

    @staticmethod
    def _collect_successor_issues(
        *,
        collector: _CompileCollector,
        specs: list[dict[str, Any]],
        source_label: str,
        authored_path_prefix: str,
        field_name: str,
    ) -> None:
        for index, spec in enumerate(specs):
            canonical_ref = _coerce_text(spec.get("successor_ref"))
            if not canonical_ref:
                continue
            authored_ref = _coerce_text(spec.get("authored_successor_ref")) or canonical_ref
            subject_label = StoryCompiler._diagnostic_subject_label(
                source_label=source_label,
                spec=spec,
                field_name=field_name,
                index=index,
            )
            collector.add_pending(
                code=ISSUE_DANGLING_SUCCESSOR_REF,
                subject_label=subject_label,
                authored_path=f"{authored_path_prefix}[{index}]",
                related_identifiers=[canonical_ref],
                details={
                    "field": field_name,
                    "authored_ref": authored_ref,
                    "canonical_ref": canonical_ref,
                },
            )

    @staticmethod
    def _collect_provider_ref_issues(
        *,
        collector: _CompileCollector,
        specs: list[dict[str, Any]],
        source_label: str,
        authored_path_prefix: str,
        field_name: str,
        issue_code: str,
        reference_keys: tuple[str, str],
    ) -> None:
        for index, spec in enumerate(specs):
            reference_key, identifier = StoryCompiler._first_reference(spec, *reference_keys)
            if not identifier:
                continue
            subject_label = StoryCompiler._diagnostic_subject_label(
                source_label=source_label,
                spec=spec,
                field_name=field_name,
                index=index,
            )
            collector.add_pending(
                code=issue_code,
                subject_label=subject_label,
                authored_path=f"{authored_path_prefix}[{index}]",
                related_identifiers=[identifier],
                details={
                    "reference_key": reference_key,
                    "missing_ref": identifier,
                },
            )

    @staticmethod
    def _first_reference(spec: dict[str, Any], *keys: str) -> tuple[str, str | None]:
        for key in keys:
            value = _coerce_text(spec.get(key))
            if value:
                return key, value
        return keys[0], None

    @staticmethod
    def _diagnostic_subject_label(
        *,
        source_label: str,
        spec: dict[str, Any],
        field_name: str,
        index: int,
    ) -> str:
        explicit_label = _coerce_text(spec.get("label"))
        if explicit_label:
            return f"{source_label}.{explicit_label}"
        return f"{source_label}.{field_name}[{index}]"

    @staticmethod
    def _resolve_entry_template_ids(
        *,
        metadata: dict[str, Any],
        registry: TemplateRegistry,
    ) -> tuple[list[str], str]:
        """Resolve compile-time entry template ids using authored priority rules."""
        start_at = metadata.get("start_at")
        if isinstance(start_at, str) and start_at:
            return [start_at], "metadata.start_at"
        if isinstance(start_at, list):
            values = [str(v) for v in start_at if str(v)]
            if values:
                return values, "metadata.start_at"

        block_templates = [
            template
            for template in registry.values()
            if hasattr(template, "has_payload_kind") and template.has_payload_kind(Block)
        ]

        for tag_name in ("start", "entry"):
            for template in block_templates:
                if template.has_tags({tag_name}):
                    return [template.get_label()], f"tag:{tag_name}"

        for template in block_templates:
            payload = getattr(template, "payload", None)
            if payload is None:
                continue
            block_locals = getattr(payload, "locals", None) or {}
            if isinstance(block_locals, dict) and (
                block_locals.get("is_start") or block_locals.get("start_at")
            ):
                return [template.get_label()], "locals:start"

        for template in block_templates:
            label = template.get_label()
            short_label = label.rsplit(".", 1)[-1] if "." in label else label
            if short_label.lower() == "start":
                return [label], "label:start"

        first_block = registry.find_one(Selector(has_payload_kind=Block))
        if first_block is not None:
            return [first_block.get_label()], "first_block"

        return [], "none"

    @staticmethod
    def _next_block_label(
        blocks: list[tuple[str, dict[str, Any]]],
        current_index: int,
        scene_label: str,
    ) -> str | None:
        next_index = current_index + 1
        if next_index >= len(blocks):
            return None
        return f"{scene_label}.{blocks[next_index][0]}"

    def _resolve_kind(self, raw_kind: Any, *, fallback: type[Entity]) -> type[Entity]:
        if isinstance(raw_kind, type):
            mapped = self._map_external_kind(raw_kind.__name__, fallback=fallback)
            if mapped is not fallback or raw_kind is fallback:
                return mapped
            if issubclass(raw_kind, Entity):
                return raw_kind
            return fallback

        if isinstance(raw_kind, str):
            mapped = self._map_external_kind(raw_kind.split(".")[-1], fallback=fallback)
            if mapped is not fallback:
                return mapped
            try:
                module_name, class_name = raw_kind.rsplit(".", 1)
                cls = getattr(import_module(module_name), class_name)
                if isinstance(cls, type):
                    mapped = self._map_external_kind(cls.__name__, fallback=fallback)
                    if mapped is not fallback:
                        return mapped
                    if issubclass(cls, Entity):
                        return cls
            except Exception:
                return fallback

        return fallback

    @staticmethod
    def _map_external_kind(kind_name: str, *, fallback: type[Entity]) -> type[Entity]:
        mapping: dict[str, type[Entity]] = {
            "Actor": Actor,
            "Location": Location,
            "Role": Actor,
            "Setting": Location,
            "Scene": Scene,
            "Block": Block,
            "MenuBlock": MenuBlock,
            "Action": Action,
            "Node": TraversableNode,
            "TraversableNode": TraversableNode,
        }
        return mapping.get(kind_name, fallback)

    @staticmethod
    def _build_payload(kind: type[Entity], payload: dict[str, Any], default_label: str) -> Entity:
        payload = dict(payload)

        if isinstance(payload.get("effects"), list):
            normalized_effects: list[dict[str, Any]] = []
            for effect in payload["effects"]:
                if isinstance(effect, str):
                    normalized_effects.append({"expr": effect})
                elif isinstance(effect, dict):
                    normalized_effects.append(dict(effect))
            payload["effects"] = normalized_effects

        if kind is Action:
            if payload.get("successor_ref") is None:
                mapped_ref = (
                    payload.get("successor")
                    or payload.get("next")
                    or payload.get("target_ref")
                    or payload.get("target_node")
                )
                if mapped_ref is not None:
                    payload["successor_ref"] = mapped_ref
            if not payload.get("text") and payload.get("content"):
                payload["text"] = payload.get("content")

        if issubclass(kind, Block) and payload.get("_is_anonymous"):
            payload["is_anonymous"] = True

        allowed = set(getattr(kind, "model_fields", {}).keys())
        filtered = {k: v for k, v in payload.items() if k in allowed}
        filtered.setdefault("label", payload.get("label") or default_label)

        try:
            return kind(**filtered)
        except Exception:
            fallback = TraversableNode(label=filtered.get("label", default_label))
            if "locals" in payload and isinstance(payload["locals"], dict):
                fallback.locals.update(payload["locals"])
            return fallback
