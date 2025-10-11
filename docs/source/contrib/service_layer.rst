Service Layer Architecture
==========================

The service layer provides a stable API between StoryTangl applications and the
engine core objects such as :class:`tangl.vm.Ledger` and
:class:`tangl.vm.Frame`. This document captures the modern orchestrator-based
approach that replaces the legacy ``ServiceManager`` pattern.


Orchestrator
------------

The :class:`~tangl.service.Orchestrator` coordinates endpoint execution and
keeps controller logic focused on domain rules:

1. Maps endpoint names to controller methods through
   :class:`~tangl.service.api_endpoint.ApiEndpoint` annotations.
2. Hydrates resources (``User``, ``Ledger``, ``Frame``) based on method type
   hints. Controllers simply declare what they need.
3. Loads objects from persistence once per request and writes back any mutated
   resources on exit.
4. Returns raw controller results—fragments, dictionaries, Pydantic models—so
   transport adapters (CLI, REST, etc.) decide how to serialize responses.


Controllers
-----------

Controllers are small classes that bundle related API endpoints. Each public
method should be decorated with :meth:`~tangl.service.ApiEndpoint.annotate` and
use type hints for automatic resource injection.

- Methods may accept ``ledger: Ledger``, ``frame: Frame`` or ``user: User``
  parameters. The orchestrator resolves them before execution.
- Implement pure domain logic inside the method. No persistence or transport
  concerns should leak into controllers.
- Return raw, serializable results. Adapters are responsible for formatting the
  response for a CLI, REST API, or other presentation surface.


Adding an Endpoint
------------------

Follow this checklist when introducing a new endpoint:

1. Add a method to the appropriate controller class.
2. Decorate it with ``@ApiEndpoint.annotate(...)`` including the access level
   and method type.
3. Declare the required resources via type hints so the orchestrator can inject
   them.
4. Return raw data structures. The orchestrator will handle persistence write
   back when the endpoint mutates state.

Example::

    from tangl.service.api_endpoint import AccessLevel, ApiEndpoint, HasApiEndpoints, MethodType
    from tangl.vm import Ledger


    class MyController(HasApiEndpoints):

        @ApiEndpoint.annotate(
            access_level=AccessLevel.PUBLIC,
            method_type=MethodType.READ,
        )
        def describe_world(self, ledger: Ledger, world_id: str) -> dict[str, str]:
            world = ledger.worlds[world_id]
            return {"world_id": world_id, "title": world.label}


Legacy ServiceManager
---------------------

``ServiceManager`` is still available for backwards compatibility but is now
deprecated. New integrations should rely on the orchestrator, and existing
callers should plan migrations to benefit from type-hint-driven resource
hydration and simplified controller logic.
