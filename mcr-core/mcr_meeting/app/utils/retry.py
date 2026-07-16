from collections.abc import Callable
from typing import ParamSpec, TypeVar

from loguru import logger
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

P = ParamSpec("P")
T = TypeVar("T")


def _log_retry(state: RetryCallState) -> None:
    logger.warning(
        "Retry {fn} attempt={n} after {exc}",
        fn=state.fn.__name__ if state.fn else "?",
        n=state.attempt_number,
        exc=state.outcome.exception() if state.outcome else None,
    )


def retry_transient(
    *,
    on: tuple[type[BaseException], ...],
    attempts: int,
    initial_delay: float,
    max_delay: float,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    return retry(  # type: ignore[no-any-return]
        retry=retry_if_exception_type(on),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=initial_delay, max=max_delay),
        before_sleep=_log_retry,
        reraise=True,
    )
