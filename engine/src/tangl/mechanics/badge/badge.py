from __future__ import annotations

import pydantic
from typing import *
import itertools
import re

from pydantic import Field

from tangl.type_hints import UniqueLabel, Expr
from tangl.utils.topological_sort import topological_sort
from tangl.core import TaskHandler
from tangl.core import Singleton
from tangl.core import HasEffects, HasConditions, HasContext, Renderable, on_render, on_gather_context, on_check_conditions
from tangl.core import Associating, on_associate, on_disassociate, on_can_associate, on_can_disassociate


class BadgeHandler:

    @classmethod
    def add_badge(cls, node: HasBadges, badge: BadgeLike):
        badge = cls.normalize_badgelike(badge)
        if not badge.check_satisfied_by(node):
            raise RuntimeError(f"Cannot add badge {badge.label} to {node.label}")
        node.associate_with(badge, as_parent=False)
        cls.compute_dynamic_badges(node)

    @classmethod
    def discard_badge(cls, node: HasBadges, badge: BadgeLike):
        badge = cls.normalize_badgelike(badge)
        node.disassociate_from(badge)
        cls.compute_dynamic_badges(node)

    @classmethod
    def compute_dynamic_badges(cls, node: HasBadges):
        """
        Evaluates all dynamic badges according to their dependencies and
        associates them.

        Must be called explicitly in a watcher whenever the badge conditions
        for a node might have changed.
        """
        # clear non-permanent dynamic badges
        for child in node.children:
            if isinstance(child, Badge) and not child.permanent:
                # do _not_ call cls.discard here or inf recursion
                node.disassociate_from(child)
        # reassign dynamic badges
        for badge in Badge.evaluation_order():
            if badge.check_satisfied_by(node):
                # do _not_ call cls.add here or inf recursion
                node.associate_with(badge)

    @classmethod
    def normalize_badgelike(cls, badge: BadgeLike, badge_cls: Type[Badge] = None) -> Badge:
        badge_cls = badge_cls or Badge
        if isinstance(badge, UniqueLabel):
            return badge_cls.get_instance(badge)
        elif isinstance(badge, Singleton):
            return badge
        raise RuntimeError(f"Unable to normalize arg badge: {badge} as a Badge ({type(badge)}, {badge_cls}")


class Badge(HasEffects, HasConditions, Renderable, Associating, Singleton):
    """
    A Badge is an intangible asset-like SingletonEntity that can be associated
    conditionally with StoryNodes.

    Unlike discrete assets, they are not wrapped in nodes, and unlike fungible
    assets, they are not counted.  The shared singleton's uid is added or removed
    directly to a node's children.

    There are several modes for badge assignment:

    - Manual Attachment (default): These nodes must be assigned specifically,
     if attachment conditions exist, they are checked only once, on assignment.

    - Dynamic Attachment: These nodes will be dynamically assigned
      whenever the attachment conditions are satisfied.

    - Manual Detachment: These "permanent" nodes must be removed specifically,
      if detachment conditions exist, they are checked only once, on removal.

    - Dynamic Detachment: These nodes will be dynamically removed whenever
      the detachment conditions are satisfied.  If there are no explicit detachment
      conditions, the unsatisfied attachment conditions are used.

    Methods for adding, discarding, and testing badges are added to
    HasBadges namespaces to support effects and conditions:

    >>> player.add_badge(Badge('this'))
    >>> player.add_badge(Badge('that'))
    >>> assert player.has_badges('this', 'that'): ...
    >>> Badge("sick", dynamic_attach=True, attachment_condition="player.state=='sick'")
    >>> assert not player.has_badges('sick')
    >>> player.state = "sick"
    >>> player.update_badges()
    >>> assert player.has_badges('sick')
    """

    dynamic_attach: bool = False
    conditions: list[Expr] = Field(default_factory=list, alias="attach_conditions")
    dynamic_detach: bool = False
    detach_conditions: list[Expr] = Field(default_factory=list)

    # Badges superseded by this one should be hidden for render
    hides: set[Badge] = Field( default_factory=set )

    @pydantic.field_validator('hides', mode="before")
    @classmethod
    def _normalize_hides(cls, value):
        # load-ordering is important
        return { BadgeHandler.normalize_badgelike(b, cls) for b in value }

    @classmethod
    def _dependency_dict(cls) -> dict[Badge, list[Badge]]:
        badge_dependency_dict = {}
        dynamic_badges = { k: v for k, v in Badge._instances.items()
                           if isinstance(v, Badge)}

        badge_names = dynamic_badges.keys()

        for badge in dynamic_badges.values():
            # this will find all badge uids in the condition strings
            badge_uids_in_conditions = [re.findall("|".join(badge_names), condition) for condition in badge.conditions]
            badge_uids_in_conditions = list(itertools.chain.from_iterable(badge_uids_in_conditions))

            # this will find all badge uids in the hides set
            badge_uids_in_hides = [hidden_badge.label for hidden_badge in badge.hides]

            # merge the two lists and remove duplicates
            dependencies = list(set(badge_uids_in_conditions + badge_uids_in_hides))

            # store in the dictionary
            badge_dependency_dict[badge.label] = dependencies
        return badge_dependency_dict

    _evaluation_order: ClassVar[list[Badge]] = None

    @classmethod
    def evaluation_order(cls) -> list[Badge]:
        """
        Topological dependency ordering of badges to compute dynamic
        badge assignments.  Evaluate dynamic badges using the returned
        ordering.

        Cached, clear by clearing the underlying _evaluation_order prop.

        :return: Sorted evaluation order for all dynamic badges.
        """
        if not cls._evaluation_order:
            badge_dependency_dict = cls._dependency_dict()
            badge_evaluation_order = list(reversed(topological_sort(badge_dependency_dict)))
            cls._evaluation_order = [Badge.get_instance(v) for v in badge_evaluation_order]
        return cls._evaluation_order

    @classmethod
    def associate_with(self, **kwargs):
        # Irrelevant, it's frozen and has no children
        pass

    @classmethod
    def disassociate_from(cls, **kwargs):
        # Irrelevant
        pass

    @on_can_disassociate.register()
    def _check_detach_conditions(self, other: HasBadges, **kwargs):
        if self.dynamic_detach and not self.detach_conditions:
            return not ConditionHandler.check_conditions_satisfied_by(self.conditions, other)
        elif self.detach_conditions:
            return ConditionHandler.check_conditions_satisfied_by(self.detach_conditions, other)
        return True


class HasBadges(Associating):
    """Story node mixin for handling badges."""

    # @pydantic.model_validator(mode="after")
    # def _compute_dynamic_badges(self):
    #     try:
    #         self.compute_dynamic_badges()
    #     except KeyError:
    #         # probably trying to restructure before graph dependencies are complete
    #         pass
    #     return self

    @property
    def badges(self: HasBadges) -> set[Badge]:
        all_badges = set( self.find_children(Badge) )           # type: set[Badge]
        hidden = set( n for b in all_badges for n in b.hides )  # type: set[Badge]
        return all_badges - hidden

    def add_badge(self, badge: BadgeLike):
        return BadgeHandler.add_badge(self, badge)

    def discard_badge(self, badge: BadgeLike):
        return BadgeHandler.discard_badge(self, badge)

    def has_badges(self, *badges: BadgeLike) -> bool:
        # Converts labels to badges, follows `has_tags` syntax convention
        query_badges = set()
        for badge in badges:
            badge = BadgeHandler.normalize_badgelike(badge)
            query_badges.add( badge )
        return query_badges.issubset(self.badges)

    def compute_dynamic_badges(self):
        BadgeHandler.compute_dynamic_badges(self)

    @on_gather_context.register()
    def _include_badges_in_ns(self) -> Mapping:
        return {
            'badges': self.badges,
            'add_badge': self.add_badge,
            'discard_badge': self.discard_badge,
            'has_badges': self.has_badges  # method to check if badge is present by name
        }

    @on_render.register()
    def _include_badges_in_render(self, **kwargs):
        return {'badges': [ self.render(b) for b in self.badges ] }

BadgeLike = Badge | UniqueLabel
