from uuid import UUID
import logging
from typing import Any
from inspect import isclass

from pydantic import Field, PrivateAttr

from tangl.core import Entity
from tangl.core.singleton import Singleton
from tangl.core.graph import Token

logger = logging.getLogger(__name__)


class TokenFactory(Entity):
    """
    Factory for creating Token nodes from Singleton bases.

    CRITICAL: TokenFactory NEVER creates Singleton bases.
    It only finds existing bases and wraps them into Tokens.

    Singleton bases must be created via:
    - Singleton(label=..., **kwargs)
    - Singleton.load_instances(data)
    - Singleton.load_instances_from_yaml(pkg, file)

    Usage:
        # Register types
        factory = TokenFactory()
        factory.register_type(NPC)
        factory.register_type(Weapon)

        # Create bases (NOT via factory!)
        NPC(label="guard", hp=100)
        Weapon(label="sword", damage=10)

        # Resolve and wrap
        base = factory.resolve_base(token_type=NPC, label="guard")
        token = factory.wrap(base, hp=85)  # hp is instance_var

        # Or convenience: resolve + wrap
        token = factory.materialize_token(
            token_type=NPC,
            label="guard",
            hp=85
        )
    """

    _types: dict[str, type[Singleton]] = PrivateAttr(default_factory=dict)

    def register_type(self, token_type: type[Singleton]) -> None:
        """
        Register a Singleton type for token creation.

        Args:
            token_type: Singleton subclass

        Examples:
            factory.register_type(NPC)
            factory.register_type(Weapon)
        """
        if not (isclass(token_type) and issubclass(token_type, Singleton)):
            raise ValueError(f"{token_type} must be Singleton subclass")

        key = f"{token_type.__module__}.{token_type.__qualname__}"
        self._types[key] = token_type
        logger.debug(f"Registered token type: {token_type.__name__}")

    def has_type(self, token_type: type[Singleton]) -> bool:
        """Check if type is registered."""
        key = f"{token_type.__module__}.{token_type.__qualname__}"
        return key in self._types

    def get_type(self, type_name: str) -> type[Singleton] | None:
        """Get type by name."""
        return self._types.get(type_name)

    def registered_types(self) -> list[type[Singleton]]:
        """List all registered types."""
        return list(self._types.values())

    # === Rest of API stays the same ===

    def resolve_base(
            self,
            token_type: type[Singleton],
            *,
            label: str | None = None,
            uuid: UUID | None = None,
            **criteria
    ) -> Singleton | None:
        """
        Find existing Singleton base. NEVER creates.

        Args:
            token_type: Singleton class to search
            label: Exact label to find
            uuid: Exact UUID to find
            **criteria: Additional search criteria

        Returns:
            Singleton instance, or None if not found

        Examples:
            # By label
            base = factory.resolve_base(NPC, label="guard")

            # By UUID
            base = factory.resolve_base(NPC, uuid=some_uuid)

            # By criteria
            base = factory.resolve_base(
                Weapon,
                has_tags={"melee"},
                damage__gte=10
            )

        CRITICAL: This never creates bases. Returns None if not found.
        """
        if not self.has_type(token_type):
            logger.warning(f"Token type not registered: {token_type.__name__}")
            return None

        # Delegate to Singleton's own registry
        if uuid is not None:
            return token_type.get_instance(uuid)
        if label is not None:
            return token_type.get_instance(label)
        if criteria:
            return token_type.find_instance(**criteria)

        logger.error("resolve_base requires label, uuid, or criteria")
        return None

    def wrap(
            self,
            base: Singleton,
            *,
            overlay: dict[str, Any] | None = None,
            **overlay_kw
    ) -> Token:
        """
        Wrap Singleton base into Token node with instance var overlay.

        Args:
            base: Singleton instance to wrap
            overlay: Dict of instance_var fields
            **overlay_kw: Convenience for overlay fields

        Returns:
            Token[T] instance (unattached to graph)

        Examples:
            guard_base = NPC.get_instance("guard")

            # With dict overlay
            token = factory.wrap(guard_base, overlay={"hp": 85})

            # With kwargs
            token = factory.wrap(guard_base, hp=85, name="John")

        Note:
            Token is created but NOT added to graph.
            Caller must: graph.add(token)
        """
        merged_overlay = {**(overlay or {}), **overlay_kw}
        token_cls = Token[base.__class__]
        return token_cls(label=base.label, **merged_overlay)

    def materialize_token(
            self,
            *,
            token_type: type[Singleton] | None = None,
            label: str | None = None,
            uuid: UUID | None = None,
            base: Singleton | None = None,
            overlay: dict[str, Any] | None = None,
            **overlay_kw
    ) -> Token | None:
        """
        Convenience: resolve base + wrap.

        Either provide:
        - base (direct), OR
        - token_type + (label OR uuid OR criteria)

        Args:
            token_type: Type to search
            label: Label to find
            uuid: UUID to find
            base: Pre-resolved base
            overlay: Instance var values
            **overlay_kw: Instance var values

        Returns:
            Token instance, or None if base not found

        Examples:
            # With base
            base = NPC.get_instance("guard")
            token = factory.materialize_token(base=base, hp=85)

            # With type + label
            token = factory.materialize_token(
                token_type=NPC,
                label="guard",
                hp=85
            )

            # With criteria (in overlay_kw)
            token = factory.materialize_token(
                token_type=Weapon,
                label="sword",
                wielder=guard_id
            )

        Returns:
            Token instance (unattached), or None if base not found
        """
        if base is not None:
            return self.wrap(base, overlay=overlay, **overlay_kw)

        if token_type is None:
            raise ValueError("Must provide base or token_type")

        base = self.resolve_base(token_type, label=label, uuid=uuid)
        if base is None:
            logger.warning(
                f"Cannot materialize token: "
                f"{token_type.__name__}(label={label}, uuid={uuid}) not found"
            )
            return None

        return self.wrap(base, overlay=overlay, **overlay_kw)

    # === Helper methods ===

    def all_bases(self, token_type: type[Singleton] | None = None) -> list[Singleton]:
        """
        List all Singleton bases.

        Args:
            token_type: Optional type filter

        Returns:
            List of Singleton instances

        Examples:
            # All bases
            bases = factory.all_bases()

            # Just NPCs
            npcs = factory.all_bases(NPC)
        """
        if token_type:
            if not self.has_type(token_type):
                return []
            return list(token_type.all_instances())

        # All types
        result = []
        for token_type_ in self.registered_types():
            result.extend(token_type_.all_instances())
        return result
