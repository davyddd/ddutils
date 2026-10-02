import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Hashable
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar, get_args

_T = TypeVar('_T')
_CreateFuncType = Callable[..., _T] | Callable[..., Awaitable[_T]]
_ScopeKey = Hashable
_ScopeFuncType = Callable[[], _ScopeKey]


class ScopedRegistry(Generic[_T]):
    """One value per scope; the scope key comes from `scope_func` (e.g. `asyncio.current_task`, `os.getpid`)."""

    __slots__ = ('create_func', 'scope_func', 'registry', 'destructor_method_name', '_lock', '__orig_class__')

    def __init__(
        self,
        create_func: _CreateFuncType,
        scope_func: _ScopeFuncType,
        destructor_method_name: str | None = None,
    ) -> None:
        self.create_func = create_func
        self.scope_func = scope_func
        self.registry: dict[_ScopeKey, _T] = {}
        self.destructor_method_name = destructor_method_name
        self._lock = asyncio.Lock()

    @property
    def generic_type(self) -> type[_T]:
        orig_class = getattr(self, '__orig_class__', None)
        try:
            return get_args(orig_class)[0]
        except IndexError as e:
            raise TypeError('Cannot determine generic type parameter') from e

    def _get_scope_key(self) -> _ScopeKey:
        key = self.scope_func()
        if key is None or not isinstance(key, Hashable):
            raise RuntimeError(f'scope_func must return a hashable scope key, got {key!r}')
        return key

    def get(self) -> _T | None:
        return self.registry.get(self._get_scope_key())

    async def _set(self, **kwargs: Any) -> tuple[_T, bool]:
        """Returns the value of the current scope and whether this call created it."""
        key = self._get_scope_key()
        if key in self.registry:
            return self.registry[key], False

        async with self._lock:
            if key in self.registry:
                return self.registry[key], False
            result = self.create_func(**kwargs)
            self.registry[key] = await result if inspect.isawaitable(result) else result
            return self.registry[key], True

    async def set(self, **kwargs: Any) -> _T:
        """Returns the value of the current scope, creating it with `create_func(**kwargs)` if needed."""
        value, _ = await self._set(**kwargs)
        return value

    async def clear(self) -> None:
        """Removes the value of the current scope and calls its destructor."""
        instance = self.registry.pop(self._get_scope_key(), None)
        destructor = getattr(instance, self.destructor_method_name or '', None)
        if destructor is not None:
            result = destructor()
            if inspect.isawaitable(result):
                await result

    @asynccontextmanager
    async def scope(self, **kwargs: Any) -> AsyncIterator[_T]:
        """
        Enters the current scope: joins the existing value or creates one. Only the block that created the
        value removes it (and calls the destructor) on exit; nested blocks join and leave it alone.
        """
        value, created = await self._set(**kwargs)
        try:
            yield value
        finally:
            if created:
                await self.clear()
