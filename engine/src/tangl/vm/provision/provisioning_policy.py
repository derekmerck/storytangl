"""Provisioning policy flags for requirement resolution."""

from enum import Flag, auto


class ProvisioningPolicy(Flag):
    """
    Provisioning strategies for satisfying a requirement.

    - **EXISTING**: Find a pre-existing provider by identifier and/or match criteria.
    - **UPDATE**: Find a provider and update it using a template (in-place edit).
    - **CREATE_TEMPLATE**: Create a new provider from a template.
    - **CREATE_TOKEN**: Create a new token from a token factory reference.
    - **CLONE**: Find a reference provider, make a copy, then evolve via template.
    - **ANY**: Any of Existing, Update, Create Template, Create Token
    - **NOOP**: No-op operation (Unsatisfiable and not allowed on Requirement)

    Notes
    -----
    Validation ensures the presence of ``identifier/criteria`` for EXISTING-family
    policies and a ``template`` for CREATE_TEMPLATE/UPDATE/CLONE.
    """

    EXISTING = auto()  # find by identifier and/or criteria match
    UPDATE = auto()  # find and update from template
    CREATE = auto()  # create from template
    CREATE_TEMPLATE = CREATE
    CREATE_TOKEN = auto()  # create from token factory reference
    CLONE = auto()  # find and evolve from template

    NOOP = auto()  # not possible

    ANY = EXISTING | UPDATE | CREATE | CREATE_TOKEN
