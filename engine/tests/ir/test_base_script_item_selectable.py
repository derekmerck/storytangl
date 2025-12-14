from pydantic import Field

from tangl.core.entity import Entity
from tangl.core.graph import Node
from tangl.ir.core_ir.base_script_model import BaseScriptItem
from tangl.ir.story_ir.story_script_models import ScopeSelector


class Selector(Entity):
    ancestors_chain: list[Entity] = Field(default_factory=list)

    def ancestors(self):
        return list(self.ancestors_chain)

    def has_scope(self, scope: ScopeSelector | None) -> bool:  # pragma: no cover - delegates
        return Node.has_scope(self, scope)


def test_template_gates_on_scope_via_selector():
    template = BaseScriptItem(label="cop", scope=ScopeSelector(ancestor_tags={"town"}))

    selector_good = Selector(
        label="block", tags=set(), ancestors_chain=[Entity(label="x", tags={"town"})]
    )

    selector_bad = Selector(
        label="block", tags=set(), ancestors_chain=[Entity(label="x", tags={"dungeon"})]
    )

    assert template.matches(selector=selector_good)
    assert not template.matches(selector=selector_bad)


def test_template_matches_still_allows_inline_criteria():
    template = BaseScriptItem(label="cop")
    selector = Selector(label="anything")

    assert template.matches(selector=selector, label="cop")
    assert not template.matches(selector=selector, label="nope")


def test_selectable_mro_uses_entity_matches():
    template = BaseScriptItem(label="gate", scope=ScopeSelector(parent_label="parent"))
    selector = Selector(
        label="child", tags=set(), ancestors_chain=[Entity(label="parent")]
    )

    assert template.matches(selector=selector)
    assert template.matches(label="gate")
