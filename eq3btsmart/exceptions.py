"""Exceptions for the eq3btsmart library."""


class Eq3Exception(Exception):
    """Base exception for the eq3btsmart library."""


class Eq3ConnectionException(Eq3Exception):
    """Exception for connection errors."""


class Eq3CommandException(Eq3Exception):
    """Exception for command errors."""


class Eq3AlreadyAwaitingResponseException(Eq3Exception):
    """Exception for commands that are already awaiting a response."""


class Eq3TimeoutException(Eq3Exception):
    """Exception for timeouts."""


class Eq3StateException(Eq3Exception):
    """Exception for invalid states."""


class Eq3InternalException(Eq3Exception):
    """Exception for internal errors."""


class Eq3InvalidDataException(Eq3Exception):
    """Exception for invalid data."""
