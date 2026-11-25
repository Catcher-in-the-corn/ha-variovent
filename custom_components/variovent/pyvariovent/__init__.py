"""Local API client for Variovent / ZSA DUO-Live spots."""

from .client import VarioventClient
from .exceptions import AuthError, CannotConnect, VariventError

__all__ = ["AuthError", "CannotConnect", "VarioventClient", "VariventError"]
__version__ = "0.3.0"
