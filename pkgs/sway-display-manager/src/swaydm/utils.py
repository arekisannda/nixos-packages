import logging

_logger: logging.Logger | None = None


def setup(level: str) -> None:
    global _logger
    _logger = logging.getLogger("sway-display-manager")
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="[%(levelname)s] %(message)s",
    )


def get_logger() -> logging.Logger:
    if _logger is None:
        raise RuntimeError("logger not initialized, call setup() first")
    return _logger


def debug(msg: str) -> None:
    get_logger().debug(msg)


def info(msg: str) -> None:
    get_logger().info(msg)


def warning(msg: str) -> None:
    get_logger().warning(msg)


def error(msg: str) -> None:
    get_logger().error(msg)
