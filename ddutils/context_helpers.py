from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_suppress(*exceptions: type[BaseException]) -> AsyncIterator[None]:
    """
    `contextlib.suppress` as an async context manager, so it can share one `async with` with other async
    context managers instead of nesting a sync `with` inside:

        async with async_suppress(AlreadyAcquiredError), RedisLock(redis_client_factory, 'sync', timeout=30):
            await sync_profiles()

    Like `suppress`, it swallows only the listed exceptions raised inside the block; the block is left at the
    point of the exception.
    """
    try:  # noqa: SIM105  # suppress() is exactly what this wraps into an async context manager
        yield
    except exceptions:
        pass


__all__ = ('async_suppress',)
