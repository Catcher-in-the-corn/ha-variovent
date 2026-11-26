"""Windows-only pytest plugin: asyncio needs a TCP socketpair, which the HA test
setup would otherwise block. Harmless on Linux (import simply does nothing there)."""
try:
    import pytest_socket

    pytest_socket.disable_socket = lambda *a, **k: None
except ImportError:
    pass
