from tangl33.core import ProvisionError

class CharacterStrategy:
    """Strategy for creating/selecting character nodes."""

    def select(self, prov, req, ctx):
        """Check if provider matches requirements."""
        if 'character' not in prov.provides:
            return False
        # Match character attributes from criteria
        return all(getattr(prov, k, None) == v for k, v in req.criteria.items())

    def create(self, req, ctx):
        """Create a new character from template if needed."""
        templates = ctx.get('character_templates', {})
        template_name = req.params.get('template')
        if not template_name or template_name not in templates:
            raise ProvisionError(f"No template for character: {template_name}")

        # Create from template
        template = templates[template_name]
        return template.build(req.params)
