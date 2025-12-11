# tangl/domains/templates_demo.py
from __future__ import annotations
from tangl.core36.types import EdgeKind
from tangl.vm36.planning.offers import Offer
from tangl.vm36.planning.provision import ProvisionRequirement

# class DemoTemplateProvider(OfferProvider):
#     """
#     Offers two possible next steps from an anchor (cursor):
#       1) 'Inspect Lair' — requires a 'villain' role (can be created if missing)
#       2) 'Open Secret Door' — requires 'key' entity present (not creatable => may block)
#     """
#
#     def enumerate(self, g: Graph, facts: Facts, ctx: StepContext, anchor_uid: UUID):
#         # 1) Inspect Lair (role villain required)
#         t1 = Offer(
#             id="inspect_lair",
#             label="Inspect the lair",
#             priority=50,
#             requires=[
#                 RequireSpec(
#                     kind="role", name="villain",
#                     constraints={"label": "Annie", "tags": ["character"]},
#                     policy={"create_if_missing": True}
#                 )
#             ],
#             produce=lambda c, a: (
#                 c.say({"type":"text","text":"You inspect the lair."}),
#                 c.add_edge(a, c.create_node("tangl.core36.entity:Node", label="inspect"), TRANSITION)
#             )
#         )
#         # 2) Open Secret Door (requires key entity present; not creatable)
#         def has_secret_tag():
#             # purely illustrative guard
#             node = g.get(anchor_uid)
#             return isinstance(node, Node) and "secret" in (node.tags or set())
#         t2 = Offer(
#             id="open_secret",
#             label="Open the secret door",
#             priority=60,
#             guard=lambda g,f,ctx,a: has_secret_tag(),
#             requires=[
#                 RequireSpec(kind="entity", name="key",
#                             constraints={"tags": ["key"]},
#                             policy={"create_if_missing": False, "optional": False})
#             ],
#             produce=lambda c, a: c.say({"type":"text","text":"The door swings open."})
#         )
#         return (t1, t2)
#

def _guard_secret(g, facts, ctx, anchor_uid) -> bool:
    n = g.get(anchor_uid)
    tags = getattr(n, "tags", set()) or set()
    return "secret" in tags

def _produce_inspect(ctx, anchor_uid):
    # Create a next node and connect with a transition edge
    target = ctx.create_node("tangl.core36.entity:Node", label="lair_detail")
    ctx.add_edge(anchor_uid, target, EdgeKind.TRANSITION)

class DemoTemplateProvider:
    """
    Simple offer provider used by tests:
      - 'inspect_lair' (enabled if role is creatable)
      - 'open_secret' (blocked; requires a 'key' entity that we don't build)
    """
    priority = 50  # used if you sort providers/specs

    def enumerate(self, g, facts, ctx, anchor_uid) -> list[Offer]:
        return [
            Offer(
                id="inspect_lair",
                label="Inspect lair",
                requires=[
                    ProvisionRequirement(kind="role", name="villain", policy={"create_if_missing": True})
                ],
                guard=lambda g, f, c, a: True,
                produce=_produce_inspect,
            ),
            Offer(
                id="open_secret",
                label="Open secret",
                requires=[ProvisionRequirement(kind="entity", name="key")],  # not creatable → blocked
                guard=_guard_secret,  # true in the test (anchor.tags includes 'secret')
                produce=lambda ctx, a: None,
            ),
        ]