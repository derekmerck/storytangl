
def _():
    builds: list[BuildReceipt] = []
    for r in ctx.call_receipts:
        if isinstance(r.result, list):
            builds.extend([x for x in r.result if isinstance(x, BuildReceipt)])
        elif isinstance(r.result, BuildReceipt):
            builds.append(r.result)
    return PlanningReceipt.summarize(*builds)


def _collect(requirement: Requirement, *, source: str, prefix: str) -> None:
    for prov in provs:
        for offer in prov.get_offers(requirement, ctx=ctx):
            offer.label = offer.label or _label_for(requirement, prefix)
            if "source" not in offer.selection_criteria:
                offer.selection_criteria = dict(offer.selection_criteria)
                offer.selection_criteria["source"] = source
            offers.append(offer)

# Affordances visible in scope should be evaluated before dependencies so
# existing resources can satisfy requirements without provisioning new ones.
affordances = sorted(
    (
        edge
        for edge in ctx.graph.find_all(
            is_instance=Affordance,
            destination_id=cursor.uid,
        )
        if edge.requirement.provider is None
    ),
    key=lambda edge: edge.requirement.uid.int,
)
for edge in affordances:
    _collect(edge.requirement, source="affordance", prefix="aff")

# Dependencies on the frontier
dependencies = sorted(
    (
        edge
        for edge in ctx.graph.find_all(
            is_instance=Dependency,
            source_id=cursor.uid,
        )
        if edge.requirement.provider is None
    ),
    key=lambda edge: edge.requirement.uid.int,
)
for edge in dependencies:
    _collect(edge.requirement, source="dependency", prefix="dep")

return offers

@on_planning(priority=HandlerPriority.LATE)
# 2) Select + apply (NORMAL/LATE)
# @global_domain.handlers.register(phase=P.PLANNING, priority=75)
def plan_select_and_apply(cursor: Node, *, ctx: Context, **kwargs):
    """Select offers, bind providers, and emit :class:`BuildReceipt` records.

    ``ProvisionOffer.accept`` now returns a provider without side effects. This
    selector performs the binding, updates :attr:`Requirement.is_unresolvable`,
    and constructs receipts summarizing the outcome for each requirement.
    """
    # Gather offers from earlier receipts
    all_offers: list[ProvisionOffer] = []
    for r in ctx.call_receipts:
        if isinstance(r.result, list):
            all_offers.extend([x for x in r.result if isinstance(x, ProvisionOffer)])
        elif isinstance(r.result, ProvisionOffer):
            all_offers.append(r.result)

    # Coalesce by requirement uid and remember requirements on the frontier
    offers_by_req: dict[UUID, list[ProvisionOffer]] = {}
    requirements: dict[UUID, Requirement] = {}

    def include_requirement(req: Requirement) -> None:
        requirements.setdefault(req.uid, req)

    for off in all_offers:
        offers_by_req.setdefault(off.requirement.uid, []).append(off)
        include_requirement(off.requirement)

    # Include unresolved frontier requirements even when no offers were published
    for edge in cursor.edges_out(is_instance=Dependency):
        if edge.requirement.provider is not None:
            continue
        include_requirement(edge.requirement)
    for edge in cursor.edges_in(is_instance=Affordance):
        if edge.requirement.provider is not None:
            continue
        include_requirement(edge.requirement)

    # Evaluate requirements in a deterministic order for testability/debuggability.
    ordered_requirements = sorted(
        requirements.values(),
        key=lambda req: req.uid.int,
    )

    builds: list[BuildReceipt] = []
    for requirement in ordered_requirements:
        candidates = offers_by_req.get(requirement.uid, [])

        if requirement.provider is not None and not candidates:
            # Already satisfied and no new offers to evaluate.
            requirement.is_unresolvable = False
            continue

        if not candidates:
            if requirement.hard_requirement:
                requirement.is_unresolvable = True
                builds.append(
                    BuildReceipt(
                        provisioner_id=cursor.uid,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=True,
                        reason="no_offers",
                    )
                )
            else:
                builds.append(
                    BuildReceipt(
                        provisioner_id=cursor.uid,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=False,
                        reason="waived_soft",
                    )
                )
            continue

        def _candidate_sort_key(offer: ProvisionOffer) -> tuple[int, int, int]:
            source = (offer.selection_criteria or {}).get("source")
            source_rank = 0 if source == "affordance" else 1
            return (source_rank, offer.priority, offer.uid.int)

        candidates.sort(key=_candidate_sort_key)

        chosen_offer: ProvisionOffer | None = None
        provider: Node | None = None
        for offer in candidates:
            candidate_provider = offer.accept(ctx=ctx)
            if candidate_provider is None:
                continue
            chosen_offer = offer
            provider = candidate_provider
            break

        if provider is None or chosen_offer is None:
            provisioner_id = (
                candidates[0].provisioner.uid if candidates else cursor.uid
            )
            if requirement.hard_requirement:
                requirement.is_unresolvable = True
                builds.append(
                    BuildReceipt(
                        provisioner_id=provisioner_id,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=True,
                        reason="unresolvable",
                    )
                )
            else:
                builds.append(
                    BuildReceipt(
                        provisioner_id=provisioner_id,
                        requirement_id=requirement.uid,
                        provider_id=None,
                        operation=ProvisioningPolicy.NOOP,
                        accepted=False,
                        hard_req=False,
                        reason="waived_soft",
                    )
                )
            continue

        # Successful binding: attach provider and clear any prior failures.
        requirement.provider = provider
        if requirement.hard_requirement:
            requirement.is_unresolvable = False

        builds.append(
            BuildReceipt(
                provisioner_id=chosen_offer.provisioner.uid,
                requirement_id=requirement.uid,
                provider_id=provider.uid,
                operation=chosen_offer.operation or ProvisioningPolicy.NOOP,
                accepted=True,
                hard_req=requirement.hard_requirement,
            )
        )

    return builds
