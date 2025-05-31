"""
tangl.core.exceptions
=====================

Specialized error types for StoryTangl domain-specific failures.

The primary exceptions include:
- ProvisionError: Failures in the requirement resolution process
"""

class ProvisionError(RuntimeError):
    ...
