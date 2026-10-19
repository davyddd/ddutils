import logging
from collections.abc import Callable, Coroutine
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any, Generic, Never, ParamSpec, TypeVar, overload

logger = logging.getLogger(__name__)

P = ParamSpec('P')
R = TypeVar('R')
D = TypeVar('D')


class _NotSet:
    def __repr__(self) -> str:
        return 'NOT_SET'


# `default_result` left at NOT_SET means "there is no fallback": the last error propagates
NOT_SET = _NotSet()


class _SafeCall(Generic[D]):
    """
    The decorator `safe_call(...)` returns: calls the function up to `1 + retries` times and, when every attempt
    fails with one of `exceptions`, returns `default_result` or re-raises the last error if none was given.
    """

    def __init__(
        self, retries: int, default_result: D | _NotSet, capture_exception: bool, exceptions: tuple[type[Exception], ...]
    ) -> None:
        if retries < 0:
            raise ValueError(f'retries must be non-negative, got {retries!r}')
        self.retries = retries
        self.default_result = default_result
        self.capture_exception = capture_exception
        self.exceptions = exceptions

    def _handle(self, error: BaseException, attempt: int) -> None:
        """Logs a failed attempt, or re-raises when it was the last one and there is no fallback."""
        if attempt == self.retries and isinstance(self.default_result, _NotSet):
            raise error
        if self.capture_exception:
            logger.exception(error)

    # `self` is annotated explicitly: without it ty does not substitute `D` in the overloads.
    # The coroutine overload goes first: `Callable[P, R]` matches a coroutine function too (with R the coroutine),
    # and the checker takes the first overload that fits.
    @overload
    def __call__(
        self: '_SafeCall[D]', func: Callable[P, Coroutine[Any, Any, R]]
    ) -> Callable[P, Coroutine[Any, Any, R | D]]: ...

    @overload
    def __call__(self: '_SafeCall[D]', func: Callable[P, R]) -> Callable[P, R | D]: ...

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapped_func(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(self.retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except self.exceptions as error:
                        self._handle(error, attempt)
                return self.default_result

            return async_wrapped_func

        @wraps(func)
        def wrapped_func(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(self.retries + 1):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as error:
                    self._handle(error, attempt)
            return self.default_result

        return wrapped_func


@overload
def safe_call(
    *, retries: int = 0, capture_exception: bool = True, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> _SafeCall[Never]: ...


@overload
def safe_call(
    *,
    default_result: D,
    retries: int = 0,
    capture_exception: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> _SafeCall[D]: ...


def safe_call(
    *,
    default_result: Any = NOT_SET,
    retries: int = 0,
    capture_exception: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> _SafeCall[Any]:
    """
    Decorator that retries a failing call and then falls back to `default_result` or re-raises.

    The function is called up to `1 + retries` times; an attempt counts as failed when it raises one of
    `exceptions`. Every failure that is retried or replaced by `default_result` is logged with the traceback
    (`capture_exception`). Without a `default_result` the last error propagates, so a `None` result always means
    the function returned `None`, never that an error was swallowed.

    A coroutine function is awaited inside the decorator, so the exceptions raised while awaiting are the ones
    handled; the result is again a coroutine function.

    Example:
        @safe_call(default_result=None, exceptions=(RedisError,), capture_exception=False)
        async def get_cached_profile(profile_id: int) -> Profile | None: ...   # None when Redis is down

        @safe_call(retries=1, exceptions=(ConnectionError,))
        def fetch(url: str) -> Response: ...   # one more try on a dropped connection, then the error
    """
    return _SafeCall(retries, default_result, capture_exception, exceptions)


__all__ = ('NOT_SET', 'safe_call')
