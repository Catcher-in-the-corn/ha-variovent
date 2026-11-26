"""Windows stub: Home Assistant's test runner imports fcntl, which POSIX-only."""
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def flock(*a, **k):
    pass


def fcntl(*a, **k):
    return 0
