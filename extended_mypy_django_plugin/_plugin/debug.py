import sys


def debug(*args: object) -> None:
    """
    Helper to print debug information to sys.stderr in a format
    that the pytest-mypy-plugins pytest plugin will ignore
    """
    print(":debug:", *args, file=sys.stdout)
