from tangl33.core import ProvisionError, ProviderCap, Tier

class CharacterStrategy:
    """Strategy for creating/selecting character nodes."""

    def select(self, prov, req, ctx):
        """Check if provider matches requirements."""
        if 'character' not in prov.provides:
            return False
        # Match character attributes from criteria
        return all(getattr(prov, k, None) == v for k, v in req.criteria.items())
    #
    # def create(self, req, ctx):
    #     """Create a new character from template if needed."""
    #     registry = ctx["templates"]
    #     tpl_name = req.params.get("template")
    #     tpl = registry.get(tpl_name)
    #     if not tpl:
    #         raise ProvisionError(f"No template for character: {tpl_name}")
    #     return tpl.build(ctx)

    def create(self, req, ctx):
        registry = ctx["templates"]
        tpl_name = req.params.get("template")
        tpl = registry.get(tpl_name)
        if not tpl:
            raise ProvisionError(f"No template for character: {tpl_name}")

        # todo: do this _in_ create or in resolver?
        node = tpl.build(ctx)                      # returns StoryNode
        graph = ctx["graph"]                       # pass graph in resolver context
        graph.add(node)

        # wrap the node in a provider-cap and register that
        cap = ProviderCap(
            owner_uid=node.uid,
            provides={"character"},
            tier=Tier.GRAPH
        )
        return cap
