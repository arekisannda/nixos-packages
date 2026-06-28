import logging

TRACE = 5
logging.addLevelName(TRACE, "TRACE")
logging.TRACE = TRACE

_logger: logging.Logger | None = None


class PerLevelFormatter(logging.Formatter):
    default_fmt = "%(levelname_padded)s %(message)s"
    trace_fmt = (
        "%(levelname_padded)s [%(module)s.%(funcName)s:%(lineno)d]: %(message)s"
    )

    def format(self, record: logging.LogRecord):
        record.levelname_padded = f'[{record.levelname}]'.ljust(10)
        if record.levelno == TRACE:
            self._style._fmt = self.trace_fmt
        else:
            self._style._fmt = self.default_fmt
        return super().format(record)


def setup(level: str) -> None:
    global _logger
    _logger = logging.getLogger("sway-display-manager")
    _logger.setLevel(getattr(logging, level.upper()))

    handler = logging.StreamHandler()
    handler.setFormatter(PerLevelFormatter())
    _logger.addHandler(handler)
    _logger.propagate = False


def get_logger() -> logging.Logger:
    if _logger is None:
        raise RuntimeError("logger not initialized, call setup() first")
    return _logger


def trace(msg: str) -> None:
    get_logger().log(TRACE, msg, stacklevel=2)


def debug(msg: str) -> None:
    get_logger().debug(msg, stacklevel=2)


def info(msg: str) -> None:
    get_logger().info(msg, stacklevel=2)


def warning(msg: str) -> None:
    get_logger().warning(msg, stacklevel=2)


def error(msg: str) -> None:
    get_logger().error(msg, stacklevel=2)
