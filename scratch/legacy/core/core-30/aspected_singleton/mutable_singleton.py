import logging

from pydantic import ConfigDict, BaseModel

from .singleton import Singleton

logger = logging.getLogger(__name__)

class MutableSingleton(Singleton, BaseModel):
    """
    MutableSingleton can update uid's dynamically based on a digested
    "secret".  This requires careful management of any instance directories.
    """
    # Potential additional features to consider:
    # - Add history tracking of previous identities
    # - Add callbacks for identity changes
    # - Add read-only property for immutable reference to current secret
    # - Add context manager for temporary identity changes

    model_config = ConfigDict(frozen=False)

    secret: str

    @classmethod
    def compute_digest(cls, *, secret = None, **kwargs) -> bytes:
        logger.debug(f"Computing digest (secret: {secret})")
        if secret is None or not secret:
            raise ValueError("Cannot set digest without a secret")
        return cls.hash_value(secret)

    def __setattr__(self, key, value):
        if key == "secret":
            logger.debug("Updating secret")
            self.unregister_instance(self)
            super().__setattr__(key, value)
            self.finalize(recompute_digest=True)  # Recompute digest
        else:
            super().__setattr__(key, value)
