from __future__ import annotations
from enum import Flag, auto
from typing import Any, ClassVar, Callable, Protocol, Iterable, Iterator, TYPE_CHECKING, Mapping
from dataclasses import dataclass
from uuid import UUID, uuid4

from pydantic import ConfigDict, SkipValidation

from tangl.core38 import Entity, Record, EntityTemplate, Node, Selector, Priority, TokenFactory

if TYPE_CHECKING:
    from .requirement import Requirement, Affordance


class ProvisionPolicy(Flag):
    # For offers only
    FORCE = auto()  # forces highest priority and always allowed
    TOKEN = auto()  # indicate offer is for a token

    # Offer may include ONE of these, req may include multiple
    EXISTING = auto()
    UPDATE = auto()  # find + update
    CREATE = auto()
    CLONE = auto()   # create + update

    # for requirements only
    ANY = EXISTING | UPDATE | CREATE

    def __int__(self):
        # should be monotonic, force is lowest
        # (create | token) should probably be cheaper than create alone?
        return self.value


class ProvisionOffer(Record):
    # todo: seems like we want to attach the accepted offer to the requirement or
    #       requirement carrier, maybe exclude the callback and serialize as just the
    #       origin, policy, priority?  Or just track the accepted-offer-id in the
    #       requirement?

    model_config = ConfigDict(arbitrary_types_allowed=True)
    # has arbitrary types, don't allow serialization
    guard_unstructure: ClassVar[bool] = True

    policy: ProvisionPolicy  # but not ANY
    callback: Callable
    priority: int = Priority.NORMAL
    distance_from_caller: int = 999
    specificity: int = 0
    candidate: Any = None

    def sort_key(self):
        from .matching import offer_sort_key

        return offer_sort_key(self)


class Provisioner(Protocol):

    def get_dependency_offers(self, requirement: Requirement) -> Iterable[ProvisionOffer]:
        ...

    def get_affordance_offers(self, node: Node) -> Iterable[ProvisionOffer]:
        ...


def _next_provision_uid(*, _ctx: Any = None) -> UUID:
    """Return a deterministic uid when vm context RNG is available."""
    if _ctx is not None:
        get_random = getattr(_ctx, "get_random", None)
        if callable(get_random):
            rng = get_random()
            if hasattr(rng, "getrandbits"):
                return UUID(int=rng.getrandbits(128), version=4)
    return uuid4()


@dataclass
class FindProvisioner:

    values: SkipValidation[Iterable[Entity]]  # current graph, don't copy on create
    distance: int = 0

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                priority = Priority.NORMAL,
                distance_from_caller=self.distance,
                candidate=c,
                callback = lambda *_, _c=c, **__: _c # need to freeze ref to _this_ c
            )

    def get_affordance_offers(self, node: Node) -> Iterator[ProvisionOffer]:
        from .requirement import Affordance
        candidates = Selector(has_kind=Affordance, satisfied_by=node).filter(self.values)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "FindProvisioner",
                policy = ProvisionPolicy.EXISTING,
                priority = Priority.NORMAL,
                distance_from_caller=self.distance,
                candidate=c,
                callback = lambda *_, _c=c, **__: _c  # need to freeze ref to _this_ c
            )

@dataclass
class TemplateProvisioner:

    templates: SkipValidation[Iterable[EntityTemplate]]  # world's template registry
    distance: int = 0

    def get_dependency_offers(self, requirement: Requirement) -> Iterator[ProvisionOffer]:
        candidates = requirement.filter(self.templates)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = "TemplateProvisioner",
                policy = ProvisionPolicy.CREATE,
                priority = Priority.NORMAL,
                distance_from_caller=self.distance,
                candidate=c,
                callback = lambda *_, _c=c, **kwargs: _c.materialize(
                    uid=_next_provision_uid(_ctx=kwargs.get("_ctx"))
                ),
            )

    # Not sure what affordance providers look like in template form?


class InlineTemplateProvisioner:
    """Offer inline requirement templates as normal CREATE candidates."""

    @classmethod
    def get_dependency_offers(cls, requirement: Requirement) -> Iterable[ProvisionOffer]:
        if requirement.fallback_templ is not None:
            return [ProvisionOffer(
                origin_id=requirement.fallback_templ.get_label(),
                policy=ProvisionPolicy.CREATE,
                callback=lambda *_, _t=requirement.fallback_templ, **kwargs: _t.materialize(
                    uid=_next_provision_uid(_ctx=kwargs.get("_ctx"))
                ),
                priority=Priority.LATE,
                distance_from_caller=0,
                candidate=requirement.fallback_templ,
            )]
        return []

    # Can't have a fallback affordance, that's just a structure that's in scope?


class FallbackProvisioner:
    """Force-only emergency provider that synthesizes minimal matching entities."""

    HIGH_COST_PRIORITY = Priority.LAST + 10_000

    @classmethod
    def _extract_selector_value(cls, requirement: Requirement, key: str):
        extra = requirement.__pydantic_extra__ or {}
        return extra.get(key)

    @classmethod
    def _synthesize_entity(cls, requirement: Requirement) -> Entity | None:
        kind = cls._extract_selector_value(requirement, "has_kind") or Entity
        if not isinstance(kind, type) or not issubclass(kind, Entity):
            kind = Entity

        kwargs: dict = {}
        identifier = cls._extract_selector_value(requirement, "has_identifier")
        label = cls._extract_selector_value(requirement, "label")
        tags = cls._extract_selector_value(requirement, "has_tags")

        if isinstance(identifier, str):
            kwargs["label"] = identifier
        elif isinstance(label, str):
            kwargs["label"] = label

        if isinstance(tags, (set, list, tuple)):
            kwargs["tags"] = set(tags)
        elif isinstance(tags, str):
            kwargs["tags"] = {tags}

        try:
            candidate = kind(**kwargs)
        except Exception:
            try:
                candidate = kind()
            except Exception:
                return None
            if "label" in kwargs and hasattr(candidate, "label"):
                candidate.label = kwargs["label"]
            if "tags" in kwargs and hasattr(candidate, "tags"):
                candidate.tags = kwargs["tags"]

        if requirement.satisfied_by(candidate):
            return candidate
        return candidate

    @classmethod
    def get_dependency_offers(cls, requirement: Requirement) -> Iterable[ProvisionOffer]:
        return [ProvisionOffer(
            origin_id="FallbackProvisioner",
            policy=ProvisionPolicy.FORCE,
            priority=cls.HIGH_COST_PRIORITY,
            distance_from_caller=999_999,
            callback=lambda *_, _req=requirement, **__: cls._synthesize_entity(_req),
        )]


class TokenProvisioner:
    # todo: This doesn't work yet b/c token factory doesn't present attribs that can be filtered by req

    token_factories: Iterable[TokenFactory]  # has all token types for this provisioner

    def get_dependency_offers(self, requirement: Requirement) -> Iterable[ProvisionOffer]:

        candidates = requirement.filter(self.token_factories)
        for c in candidates:
            yield ProvisionOffer(
                origin_id = f"{c.get_label()}:{requirement.token_from}",
                policy = ProvisionPolicy.CREATE | ProvisionPolicy.TOKEN,
                callback = c.materialize(requirement.token_from),
                priority=Priority.EARLY  # tokens are considered to be cheaper than full nodes when available
            )


class UpdateCloneProvisioner:
    """Synthesizes deferred UPDATE/CLONE offers from selected FIND/CREATE offers.

    This provisioner never executes upstream callbacks while constructing offers.
    It selects the best FIND and CREATE candidates by sort key and emits deferred
    composite callbacks that sub-accept only when the composite offer itself is
    accepted by the resolver.
    """

    _REFERENCE_SELECTOR_KEYS: ClassVar[tuple[str, ...]] = (
        "reference_selector",
        "reference",
        "reference_req",
    )
    _TEMPLATE_SELECTOR_KEYS: ClassVar[tuple[str, ...]] = (
        "update_template_selector",
        "template_selector",
        "update_selector",
    )
    _STRIP_UPDATE_KEYS: ClassVar[set[str]] = {
        "kind",
        "uid",
        "registry",
        "registry_id",
        "_registry",
    }

    @classmethod
    def _coerce_selector(cls, value: Any) -> Selector | None:
        if value is None:
            return None
        if isinstance(value, Selector):
            return value
        if isinstance(value, Mapping):
            return Selector(**dict(value))
        return None

    @classmethod
    def _selector_from_requirement(
        cls,
        requirement: "Requirement",
        *,
        field_name: str,
        fallback_keys: tuple[str, ...],
    ) -> Selector | None:
        selector = cls._coerce_selector(getattr(requirement, field_name, None))
        if selector is not None:
            return selector

        extra = requirement.__pydantic_extra__ or {}
        for key in fallback_keys:
            selector = cls._coerce_selector(extra.get(key))
            if selector is not None:
                return selector
        return None

    @staticmethod
    def _offer_matches_selector(offer: ProvisionOffer, selector: Selector) -> bool:
        candidate = getattr(offer, "candidate", None)
        if candidate is None:
            return False
        try:
            return selector.matches(candidate)
        except (TypeError, ValueError):
            return False

    @classmethod
    def _best_offer(cls, offers: Iterable[ProvisionOffer]) -> ProvisionOffer | None:
        values = list(offers)
        if not values:
            return None
        values.sort(key=lambda offer: offer.sort_key())
        return values[0]

    @classmethod
    def _sanitize_updates(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: val
            for key, val in dict(value).items()
            if key not in cls._STRIP_UPDATE_KEYS
        }

    @classmethod
    def _extract_update_payload(
        cls,
        offer: ProvisionOffer,
        *,
        _ctx: Any = None,
    ) -> dict[str, Any]:
        created = offer.callback(_ctx=_ctx)
        if isinstance(created, EntityTemplate):
            return cls._sanitize_updates(created.payload.unstructure())
        if isinstance(created, Entity):
            return cls._sanitize_updates(created.unstructure())
        if isinstance(created, Mapping):
            return cls._sanitize_updates(created)

        candidate = getattr(offer, "candidate", None)
        if isinstance(candidate, EntityTemplate):
            return cls._sanitize_updates(candidate.payload.unstructure())
        return {}

    @staticmethod
    def _apply_updates_in_place(reference: Any, updates: Mapping[str, Any]) -> Any:
        if not updates:
            return reference
        if hasattr(reference, "update_attrs"):
            reference.update_attrs(**dict(updates))
            return reference
        for key, value in dict(updates).items():
            if hasattr(reference, key):
                setattr(reference, key, value)
        return reference

    @staticmethod
    def _clone_with_updates(
        reference: Any,
        updates: Mapping[str, Any],
        *,
        _ctx: Any = None,
    ) -> Any:
        if not hasattr(reference, "evolve"):
            raise TypeError(f"{type(reference).__name__} is not cloneable (missing evolve)")
        return reference.evolve(
            uid=_next_provision_uid(_ctx=_ctx),
            **dict(updates),
        )

    @classmethod
    def _make_offer(
        cls,
        *,
        policy: ProvisionPolicy,
        find_offer: ProvisionOffer,
        create_offer: ProvisionOffer,
    ) -> ProvisionOffer:
        def _accept(*_, _ctx=None, **__) -> Any:
            reference = find_offer.callback(_ctx=_ctx)
            if reference is None:
                return None
            updates = cls._extract_update_payload(create_offer, _ctx=_ctx)
            if policy & ProvisionPolicy.UPDATE:
                return cls._apply_updates_in_place(reference, updates)
            if policy & ProvisionPolicy.CLONE:
                return cls._clone_with_updates(reference, updates, _ctx=_ctx)
            return None

        distance = max(
            int(getattr(find_offer, "distance_from_caller", 999)),
            int(getattr(create_offer, "distance_from_caller", 999)),
        )
        specificity = max(
            int(getattr(find_offer, "specificity", 0)),
            int(getattr(create_offer, "specificity", 0)),
        )
        priority = max(
            int(getattr(find_offer, "priority", Priority.NORMAL)),
            int(getattr(create_offer, "priority", Priority.NORMAL)),
        )
        return ProvisionOffer(
            origin_id=f"UpdateCloneProvisioner:{policy.name.lower()}",
            policy=policy,
            callback=_accept,
            priority=priority,
            distance_from_caller=distance,
            specificity=specificity,
            candidate=getattr(find_offer, "candidate", None),
        )

    @classmethod
    def get_dependency_offers(
        cls,
        requirement: "Requirement",
        offers: Iterable[ProvisionOffer],
    ) -> list[ProvisionOffer]:
        wants_update = bool(requirement.provision_policy & ProvisionPolicy.UPDATE)
        wants_clone = bool(requirement.provision_policy & ProvisionPolicy.CLONE)
        if not (wants_update or wants_clone):
            return []

        reference_selector = cls._selector_from_requirement(
            requirement,
            field_name="reference_selector",
            fallback_keys=cls._REFERENCE_SELECTOR_KEYS,
        )
        template_selector = cls._selector_from_requirement(
            requirement,
            field_name="update_template_selector",
            fallback_keys=cls._TEMPLATE_SELECTOR_KEYS,
        )
        if reference_selector is None or template_selector is None:
            return []

        find_offers = [
            offer
            for offer in offers
            if (offer.policy & ProvisionPolicy.EXISTING)
            and cls._offer_matches_selector(offer, reference_selector)
        ]
        create_offers = [
            offer
            for offer in offers
            if (offer.policy & ProvisionPolicy.CREATE)
            and cls._offer_matches_selector(offer, template_selector)
        ]

        best_find = cls._best_offer(find_offers)
        best_create = cls._best_offer(create_offers)
        if best_find is None or best_create is None:
            return []

        synthesized: list[ProvisionOffer] = []
        if wants_update:
            synthesized.append(
                cls._make_offer(
                    policy=ProvisionPolicy.UPDATE,
                    find_offer=best_find,
                    create_offer=best_create,
                )
            )
        if wants_clone:
            synthesized.append(
                cls._make_offer(
                    policy=ProvisionPolicy.CLONE,
                    find_offer=best_find,
                    create_offer=best_create,
                )
            )
        return synthesized


# Backward-compatible alias while feature is still evolving.
CloneProvisioner = UpdateCloneProvisioner
