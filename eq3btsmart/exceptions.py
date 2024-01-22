"""Exceptions for the eq3btsmart library."""


class TemperatureException(Exception):
    """Temperature out of range error."""


class BackendException(Exception):
    """Exception to wrap backend exceptions."""
