"""Exceptions raised by pyvariovent."""


class VariventError(Exception):
    """Base error."""


class CannotConnect(VariventError):
    """The spot could not be reached."""


class AuthError(VariventError):
    """Login failed or session expired."""
