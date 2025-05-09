tangl.core.runtime
==================

Runtime support for capability registration and provider discovery.

The runtime package provides the execution environment for StoryTangl's
capability-based architecture through:

- HandlerCache: Indexed storage of capabilities by phase and tier
- ProviderRegistry: Specialized registry for requirement providers

These components optimize the performance-critical operations of 
capability resolution and provider matching, ensuring that even
complex stories with many capabilities maintain responsive traversal.

The runtime abstractions also enable specialized extensions like
hot-reloading, capability introspection, and diagnostic tooling.
