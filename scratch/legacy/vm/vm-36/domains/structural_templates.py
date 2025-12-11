# tangl/domains/structural_templates.py
from tangl.vm36.planning.offers import Offer

class StructuralTemplates:
    def templates(self, g, node):
        raw = (node.locals or {}).get("templates", [])
        for t in raw:
            yield Offer(
                id=t["id"], label=t["label"], priority=t.get("priority",50),
                requires=t.get("requires", []),    # list[RequireSpec] already serialized in locals
                guard=t.get("guard", lambda g,f,c,a: True),
                produce=t.get("produce", lambda c,a: None),
            )
