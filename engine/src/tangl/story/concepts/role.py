from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import Field, model_validator

from tangl.core import Selector
from tangl.core.bases import BaseModelPlus
from tangl.type_hints import Tag
from tangl.vm import Dependency

from ..dispatch import on_gather_ns
from .actor import Actor
from .narrator_knowledge import HasNarratorKnowledge


# Authoring keys that carry structured grant metadata rather than scalar locals.
_GRANT_RESERVED_KEYS = ("locals", "tags", "priority")


class RoleGrant(BaseModelPlus):
    """RoleGrant(locals: dict[str, Any] = {}, tags: set[Tag] = set(), priority: int = 0)

    Provider-bound grant carried on a role binding (mu-affordance, phase 1).

    Why
    ----
    A role binding should be able to decorate whoever currently fills it with
    lightweight, relationship-scoped overlays -- a title, a rank, a badge text,
    or derived tags -- without writing that state back onto the provider. The
    active binding is the source of truth: the overlay is *derived* at namespace
    gather time and disappears automatically when the binding is swapped or
    cleared. This is the narrow first slice of the broader microconcept design.

    Key Features
    ------------
    * ``locals`` carry scalar overlays (e.g. ``title``, ``rank``) projected
      under the role label as ``{label}_{key}``.
    * ``tags`` carry derived tags projected as ``{label}_tags`` and unioned into
      the merged ``grant_tags`` scope view.
    * ``priority`` orders precedence when multiple active bindings grant the same
      key into the merged ``grants`` scope view: higher priority wins; ties break
      by scope nearness (handled by gather order) then authored label.

    Authoring
    ---------
    Accepts a flat authored mapping where ``tags`` and ``priority`` are reserved
    and every other key folds into ``locals``::

        grants:
          title: "boss"
          tags: ["management"]

    is equivalent to ``RoleGrant(locals={"title": "boss"}, tags={"management"})``.

    See also
    --------
    ``docs/src/notes/MU_AFFORDANCES.md``
        Governing design note (microconcepts / mu-affordances).
    :class:`Role`
        Relationship carrier that materializes these grants onto its provider.
    """

    locals: dict[str, Any] = Field(default_factory=dict)
    tags: set[Tag] = Field(default_factory=set)
    priority: int = 0

    @model_validator(mode="before")
    @classmethod
    def _fold_flat_authoring(cls, data: Any) -> Any:
        """Fold flat authored grant mappings into the structured shape.

        Top-level keys other than ``locals``/``tags``/``priority`` are treated as
        scalar locals so authors can write the ergonomic ``{title: "boss"}`` form
        alongside the explicit ``{locals: {...}}`` form.
        """
        if not isinstance(data, Mapping):
            return data
        extra = {key: value for key, value in data.items() if key not in _GRANT_RESERVED_KEYS}
        if not extra:
            return data
        folded: dict[str, Any] = {
            key: value for key, value in data.items() if key in _GRANT_RESERVED_KEYS
        }
        merged_locals = dict(folded.get("locals") or {})
        merged_locals.update(extra)
        folded["locals"] = merged_locals
        return folded

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when the grant projects nothing."""
        return not self.locals and not self.tags


class Role(HasNarratorKnowledge, Dependency[Actor]):
    """Role()

    Story-specific dependency edge that binds an actor provider into gathered scope.

    Why
    ----
    ``Role`` turns generic dependency resolution into a narrative concept with a
    stable namespace contract, making resolved actors available under both the
    role label and derived metadata keys.

    Key Features
    ------------
    * Extends :class:`~tangl.vm.provision.requirement.Dependency` so role edges
      participate in standard provisioning and frontier resolution.
    * Publishes the resolved actor under the role label plus derived metadata
      keys such as ``guide_name``.
    * Publishes additive aliases such as ``guide_role`` and ``role_edges`` so
      templates and filters can address role-level epistemic state separately
      from provider-level knowledge.
    * Carries an optional :class:`RoleGrant` whose scalar/tag overlays are
      projected onto the currently bound provider while the binding is active.
    * Contributes a merged ``roles`` mapping during namespace gathering.

    API
    ---
    - :meth:`provide_role_symbols` returns the local symbol payload reused by
      gather-time assembly.

    See also
    --------
    :class:`Actor`
        Default provider type bound by role dependencies.
    :class:`RoleGrant`
        Provider-bound overlay declared on the role binding.
    :class:`~tangl.vm.provision.requirement.Dependency`
        Base provisioning edge contract used by story roles.
    """

    grants: RoleGrant | None = None

    @staticmethod
    def _invoke_provider_ns(provider: Any) -> dict[str, Any]:
        get_ns = getattr(provider, "get_ns", None)
        if not callable(get_ns):
            return {}

        value = get_ns()
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError(
                f"{type(provider).__name__}.get_ns must return Mapping | None",
            )

        payload = dict(value)
        return {key: item for key, item in payload.items() if item is not provider}

    def provide_role_symbols(self) -> dict[str, Any]:
        """Publish role/provider symbols for gather-time namespace assembly.

        Grant overlays are projected separately by :func:`contribute_roles` from
        the scope-resolved grant set, so that a nearer binding's grant (or its
        absence) wins for a given label.
        """
        provider = self.provider
        label = self.get_label()
        if provider is None or not label:
            return {}

        payload: dict[str, Any] = {label: provider}
        provider_ns = self._invoke_provider_ns(provider)
        for key, value in provider_ns.items():
            payload[f"{label}_{key}"] = value
        return payload


def _role_sort_key(role: Role) -> tuple[str, str]:
    return role.get_label() or "", str(role.uid)


@on_gather_ns
def contribute_roles(*, caller, ctx, **_kw):
    """Inject role providers, role metadata, and provider-bound grants into scope."""
    if not hasattr(caller, "edges_out"):
        return None

    scope_nodes = list(caller.ancestors) if hasattr(caller, "ancestors") else [caller]

    contributions: dict[str, Any] = {}
    roles: dict[str, Any] = {}
    role_edges: dict[str, Role] = {}
    # Per-label grants resolved with nearer-scope-overrides semantics: outer
    # scopes are visited first, so a nearer binding's grant (or its absence)
    # wins for a given label.
    role_grants: dict[str, RoleGrant] = {}
    for scope in reversed(scope_nodes):
        scope_roles = sorted(scope.edges_out(Selector(has_kind=Role)), key=_role_sort_key)
        for role in scope_roles:
            role_payload = role.provide_role_symbols()
            if role_payload:
                contributions.update(role_payload)
            provider = role.provider
            label = role.get_label()
            if provider is not None and label:
                roles[label] = provider
            if label:
                contributions[f"{label}_role"] = role
                role_edges[label] = role
                # Only a *bound* role owns its label's grant, mirroring how an
                # unbound nearer role does not shadow the parent's provider symbol
                # (``provide_role_symbols`` returns nothing when unbound). A nearer
                # bound role with no grant clears the parent's; an unbound nearer
                # role is an empty slot — the parent's provider and grant show
                # through unchanged.
                if provider is not None:
                    grant = role.grants
                    if grant is not None and not grant.is_empty:
                        role_grants[label] = grant
                    else:
                        role_grants.pop(label, None)

    if roles:
        contributions["roles"] = roles
    if role_edges:
        contributions["role_edges"] = role_edges

    # Project the scope-resolved grants. Label-scoped keys (``{label}_{key}`` and
    # ``{label}_tags``) are written after the provider symbols above, so a grant
    # intentionally overrides a same-named provider value. The merged scope views
    # resolve different labels granting the same key by priority (higher wins;
    # ties keep the first label in sorted order); tags simply union.
    #
    # NOTE (phase-1 convenience): ``grants``/``grant_tags`` merge scope-wide. The
    # generalized Facet model favors a per-subject merge instead -- see
    # docs/src/notes/MU_AFFORDANCES.md (Open Questions). Treat these flat views as
    # provisional, not the final contract, when promoting Facet to core.
    merged_grants: dict[str, Any] = {}
    grant_priority: dict[str, int] = {}
    grant_tags: set[Tag] = set()
    for label in sorted(role_grants):
        grant = role_grants[label]
        for key, value in grant.locals.items():
            contributions[f"{label}_{key}"] = value
            if key not in merged_grants or grant.priority > grant_priority[key]:
                merged_grants[key] = value
                grant_priority[key] = grant.priority
        if grant.tags:
            tags = set(grant.tags)
            contributions[f"{label}_tags"] = tags
            grant_tags |= tags

    if role_grants:
        contributions["role_grants"] = dict(role_grants)
    if merged_grants:
        contributions["grants"] = merged_grants
    if grant_tags:
        contributions["grant_tags"] = grant_tags

    return contributions or None
