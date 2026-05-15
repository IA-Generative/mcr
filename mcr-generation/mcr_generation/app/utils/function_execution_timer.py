import functools
import inspect
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar, cast

from loguru import logger

P = ParamSpec("P")
R = TypeVar("R")


def log_execution_time(func: Callable[P, R]) -> Callable[P, R]:
    # Async branch required: a sync wrapper around a coroutine would only time
    # its creation (~instant), not its actual execution.
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            logger.info("{} executed in {:.4f}s", func.__name__, elapsed)
            return cast(R, result)

        return cast(Callable[P, R], async_wrapper)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("{} executed in {:.4f}s", func.__name__, elapsed)
        return result

    return wrapper
