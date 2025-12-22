from tangl.core import ContentAddressable
from tangl.core.registry import Registry, VT
from tangl.core.singleton import Singleton
from tangl.core.graph import Token

class TokenFactory(Registry[Singleton]):
    """
    Register Singletons, produce tokens from singleton instances.

    Usage:
        >> f = TokenFactory()
        >> s = Singleton()
        >> Singleton(label="foo")  # creates a singleton named "foo"
        >> f.add(s)
        >> f.all_tokens()
        [ <Singleton:foo> ]
        >> foo_ref = f.find_one(is_instance=Singleton, identifier="foo")
        >> foo_tok = f.materialize_token(foo_ref)  # type is Token[Singleton]
        >> foo_tok = f.materialize_token(is_instance=Singleton, identifier="foo")  # alternative form
    """

    def all_tokens(self) -> list[Singleton]:
        result = []
        for singleton_cls in self.data.values():
            result.extend(singleton_cls._instances().values())
        return result

    def materialize_token(self, token_ref: Singleton = None, **criteria) -> ContentAddressable:
        if token_ref is None:
            token_ref = self.find_one(**criteria)

        return Token[token_ref.__class__](label=token_ref.label)

