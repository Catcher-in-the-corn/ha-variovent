"""Windows stub: Home Assistant imports the POSIX-only resource module."""
RLIMIT_NOFILE = 7


def getrlimit(*a):
    return (1024, 4096)


def setrlimit(*a):
    pass
