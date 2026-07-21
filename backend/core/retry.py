import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    retries: int = 2,
    delay_seconds: float = 0.05,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> T:
    last_error: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except exceptions as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(delay_seconds * (attempt + 1))
    assert last_error is not None
    raise last_error
