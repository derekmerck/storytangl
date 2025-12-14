from tangl.core.graph import Graph
from tangl.ir.story_ir.actor_script_models import ActorScript
from tangl.vm.provision import (
    PlannedOffer,
    ProvisioningPolicy,
    Requirement,
    TemplateProvisioner,
)


def test_build_receipt_captures_template_provenance() -> None:
    template = ActorScript(
        label="npc",
        obj_cls="tangl.story.concepts.actor.actor.Actor",
        name="NPC",
    )
    graph = Graph()
    requirement = Requirement(
        graph=graph,
        template_ref="npc",
        policy=ProvisioningPolicy.CREATE,
    )
    provisioner = TemplateProvisioner(template_registry={"npc": template}, layer="local")
    ctx = type("Ctx", (), {"graph": graph, "cursor": None, "cursor_id": None})()

    offers = list(provisioner.get_dependency_offers(requirement, ctx=ctx))
    assert len(offers) == 1

    offer = offers[0]
    planned_offer = PlannedOffer(offer=offer, requirement=requirement)
    receipt = planned_offer.execute(ctx=ctx)

    assert receipt.template_ref == "npc"
    assert receipt.template_hash == template.content_hash
    assert receipt.template_content_id == template.content_identifier()
    assert receipt.provider_id is not None

