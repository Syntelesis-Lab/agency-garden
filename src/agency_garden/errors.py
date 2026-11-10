"""Actionable errors that callers can handle without parsing messages."""

from typing import Any


class GardenError(Exception):
    """Base class for configuration, execution and evidence errors."""


class ConfigurationError(GardenError):
    """The experiment or extension cannot be used as configured."""


class IntegrityError(GardenError):
    """The recorded manifest, event chain or materialized state is inconsistent."""


class RunBlocked(GardenError):
    """A limit or an unresolved previous decision prevents further execution."""


class PolicyError(GardenError):
    """A participant response failed; retain its receipt without inventing an action."""

    def __init__(self, message: str, *, receipt: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.receipt = receipt or {}
