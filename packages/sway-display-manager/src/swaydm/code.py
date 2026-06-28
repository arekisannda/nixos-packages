import sys
from enum import IntEnum, unique


@unique
class Code(IntEnum):
    OK = 0
    ERROR = 1


def exit_with_status(code: Code) -> int:
    """Map a protocol code to a process exit code."""
    sys.exit(0 if code is Code.OK else 1)
