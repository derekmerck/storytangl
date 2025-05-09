"""
tangl.core.exceptions
=====================

Specialized error types for StoryTangl domain-specific failures.

StoryTangl uses custom exceptions to:
- Distinguish engine errors from general Python errors
- Provide context-rich error information
- Enable targeted error handling
- Support debugging and diagnostics

The primary exceptions include:
- ProvisionError: Failures in the requirement resolution process

This granular approach to error handling supports both development-time
debugging and runtime resilience in storytelling applications.
"""

class ProvisionError(RuntimeError):
    ...
