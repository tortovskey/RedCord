from __future__ import annotations

import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


class RetryExhaustedError(RuntimeError):
    pass


def retry_call(
    func: Callable[P, R],
    *args: P.args,
    attempts: int = 3,
    delay_seconds: float = 0.5,
    backoff: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: P.kwargs,
) -> R:
    """Tiny retry helper used by self-healing services."""

    last_error: BaseException | None = None
    current_delay = delay_seconds
    for _ in range(max(1, attempts)):
        try:
            return func(*args, **kwargs)
        except exceptions as exc:
            last_error = exc
            time.sleep(current_delay)
            current_delay *= backoff
    raise RetryExhaustedError(str(last_error)) from last_error
