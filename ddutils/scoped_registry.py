import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Hashable, Iterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Any, Generic, TypeVar, get_args

_T = TypeVar('_T')
_CreateFuncType = Callable[..., _T] | Callable[..., Awaitable[_T]]
_ScopeType = Hashable
_ScopeFuncType = Callable[[], _ScopeType | None]
_RegistryType = dict[_ScopeType, _T]


class ScopedRegistry(Generic[_T]):
    """
    Registry that keeps one value per scope.

    The scope key comes either from `scope_func` (e.g. `asyncio.current_task`, `os.getpid`) or, when
    `scope_func` is not given, from a `ContextVar` owned by the registry. In the latter case the key is
    set by `scope()` and inherited by every task spawned inside the block (`gather`, `TaskGroup`,
    `create_task`), so children see the same value as the parent.

    `scope()` is the single entry point into a scope: it creates the value on enter and removes it
    (calling the destructor) on exit. Nested `scope()` blocks join the existing value and leave it alone.
    """

    __slots__ = (
        'create_func',
        'scope_func',
        'registry',
        'destructor_method_name',
        '_lock',
        '_lock_loop',
        '_key_var',
        '__orig_class__',
    )

    create_func: _CreateFuncType
    scope_func: _ScopeFuncType | None
    registry: _RegistryType
    destructor_method_name: str | None

    def __init__(
        self,
        create_func: _CreateFuncType,
        scope_func: _ScopeFuncType | None = None,
        destructor_method_name: str | None = None,
    ) -> None:
        self.create_func = create_func
        self.scope_func = scope_func
        self.registry = {}
        self.destructor_method_name = destructor_method_name
        self._lock: asyncio.Lock | None = None
        self._lock_loop: asyncio.AbstractEventLoop | None = None
        self._key_var: ContextVar[_ScopeType | None] = ContextVar(f'scoped_registry_{id(self)}', default=None)

    @property
    def generic_type(self) -> type[_T]:
        orig_class = getattr(self, '__orig_class__', None)
        try:
            return get_args(orig_class)[0]
        except IndexError as e:
            raise TypeError('Cannot determine generic type parameter') from e

    # Scope key

    def _get_key(self) -> _ScopeType | None:
        if self.scope_func is not None:
            return self.scope_func()
        return self._key_var.get()

    def _require_key(self) -> _ScopeType:
        key = self._get_key()
        if key is None:
            if self.scope_func is None:
                raise RuntimeError('ScopedRegistry without scope_func is used outside of scope()')
            raise RuntimeError('scope_func returned None: there is no current scope')
        return key

    def get(self) -> _T | None:
        try:
            key = self._get_key()
        except Exception:  # noqa: BLE001
            return None
        return None if key is None else self.registry.get(key)

    # Create

    def _get_lock(self) -> asyncio.Lock:
        # `asyncio.Lock` binds to the loop on the first contended acquire; a new loop (tests, reload) gets a new lock
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock, self._lock_loop = asyncio.Lock(), loop
        return self._lock

    async def _create(self, **kwargs: Any) -> _T:
        result = self.create_func(**kwargs)
        return await result if inspect.isawaitable(result) else result

    async def _async_set(self, key: _ScopeType, **kwargs: Any) -> tuple[_T, bool]:
        """Returns the value for `key` and whether this call created it."""
        if key in self.registry:
            return self.registry[key], False

        async with self._get_lock():
            if key in self.registry:
                return self.registry[key], False
            value = await self._create(**kwargs)
            self.registry[key] = value
            return value, True

    def sync_set(self, **kwargs: Any) -> _T:
        key = self._require_key()
        if key not in self.registry:
            result = self.create_func(**kwargs)
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError('create_func returned an awaitable; use async_set instead')
            self.registry[key] = result
        return self.registry[key]

    async def async_set(self, **kwargs: Any) -> _T:
        value, _ = await self._async_set(self._require_key(), **kwargs)
        return value

    # Clear

    def _pop(self, *scopes: _ScopeType) -> Iterator[Any]:
        """Removes the given scopes (the current one by default) and yields what their destructors return."""
        if not scopes:
            key = self._get_key()
            if key is None:
                return
            scopes = (key,)

        for scope in scopes:
            if scope not in self.registry:
                continue
            instance = self.registry.pop(scope)
            if self.destructor_method_name is not None:
                destructor = getattr(instance, self.destructor_method_name, None)
                if destructor is not None:
                    yield destructor()

    def sync_clear(self, *scopes: _ScopeType) -> None:
        for result in self._pop(*scopes):
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError('destructor returned an awaitable; use async_clear instead')

    async def async_clear(self, *scopes: _ScopeType) -> None:
        for result in self._pop(*scopes):
            if inspect.isawaitable(result):
                await result

    # Scope

    @asynccontextmanager
    async def scope(self, **kwargs: Any) -> AsyncIterator[_T]:
        """
        Enters the current scope: joins the existing value or creates one with `create_func(**kwargs)`.

        Only the block that created the value removes it and calls the destructor on exit (also on an
        exception or cancellation); nested blocks join and leave the value alone. Without `scope_func` the
        outermost block also sets the context key for its duration, so tasks spawned inside see the same value.
        """
        token = None
        if self.scope_func is None and self._key_var.get() is None:
            token = self._key_var.set(object())

        try:
            key = self._require_key()
            value, created = await self._async_set(key, **kwargs)
            try:
                yield value
            finally:
                if created:
                    await self.async_clear(key)
        finally:
            if token is not None:
                self._key_var.reset(token)
