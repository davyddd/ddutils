import asyncio
import inspect
from collections.abc import AsyncIterator, Awaitable, Callable, Hashable
from contextlib import asynccontextmanager
from typing import Any, Generic, TypeVar, get_args
from uuid import uuid4

_T = TypeVar('_T')
_CreateFuncType = Callable[..., _T] | Callable[..., Awaitable[_T]]
_ScopeKey = Hashable
_ScopeFuncType = Callable[..., _ScopeKey | None]
# A `scope_func` that declares this parameter receives a freshly generated key when `scope()` is entered
# and `None` on every other access; functions without it are called with no arguments.
SCOPE_TOKEN_PARAMETER = 'token'


class ScopedRegistry(Generic[_T]):
    """
    One value per scope.

    `scope_func` decides what the current scope is and returns its key; `None` means "no current scope" and
    makes the registry raise `RuntimeError`. Plain key functions take no arguments:

        asyncio.current_task   # one value per task, a child task does not see the parent's value
        os.getpid              # one value per process

    A `scope_func` that declares a `token` parameter is meant for scopes kept in a `ContextVar`: on entering
    `scope()` (or on `set()`) it receives a freshly generated token that it may store as the key of a new scope,
    and on every other access (`get`, `clear`, a nested `scope()`) it receives `None` and must only read:

        def execution_scope(token):            # one value per execution (HTTP request, actor run),
            key = execution_key.get()          # inherited by the tasks spawned inside the block
            if key is None and token is not None:
                execution_key.set(token)
                key = token
            return key

    A scope started this way is not reset when the block ends, so `scope()` must be entered in a task that does
    not outlive the block (a request handler, an actor run); a key left in a long-living task would be
    inherited by every task spawned from it afterwards.
    """

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

    def _get_scope_func_kwargs(self, token: str | None) -> dict[str, Any]:
        kwargs = {}
        if SCOPE_TOKEN_PARAMETER in inspect.signature(self.scope_func).parameters:
            kwargs['token'] = token
        return kwargs

    def _get_scope_key(self, token: str | None = None) -> _ScopeKey:
        key = self.scope_func(**self._get_scope_func_kwargs(token))
        if key is None:
            raise RuntimeError('There is no current scope')
        if not isinstance(key, Hashable):
            raise RuntimeError(f'scope_func must return a hashable scope key, got {key!r}')
        return key

    def get(self) -> _T | None:
        return self.registry.get(self._get_scope_key())

    async def _set(self, **kwargs: Any) -> tuple[_T, bool]:
        """Returns the value of the current scope and whether this call created it; may start a new scope."""
        key = self._get_scope_key(uuid4().hex)
        if key in self.registry:
            return self.registry[key], False

        async with self._lock:
            if key in self.registry:
                return self.registry[key], False
            result = self.create_func(**kwargs)
            self.registry[key] = await result if inspect.isawaitable(result) else result
            return self.registry[key], True

    async def set(self, **kwargs: Any) -> _T:
        """
        Returns the value of the current scope, creating it with `create_func(**kwargs)` if needed.

        Prefer `scope()`: it removes what it created on exit. Whoever calls `set()` directly takes over that
        responsibility and must call `clear()` when the value is no longer needed (if it ever is: a per-process
        client may live until the process ends). A `scope_func` with a `token` parameter may start a new scope here.
        """
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
        A `scope_func` with a `token` parameter is offered a fresh token here and may start a new scope with it.
        """
        value, created = await self._set(**kwargs)
        try:
            yield value
        finally:
            if created:
                await self.clear()
