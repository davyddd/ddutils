import inspect
from collections.abc import Awaitable, Hashable
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar, Union, get_args

_T = TypeVar('_T', bound=Any)
_CreateFuncType = Union[Callable[..., _T], Callable[..., Awaitable[_T]]]
_ScopeType = Hashable
_ScopeFuncType = Callable[[], _ScopeType]
_RegistryType = Dict[_ScopeType, _T]


class ScopedRegistry(Generic[_T]):
    __slots__ = 'create_func', 'scope_func', 'registry', 'destructor_method_name', '__orig_class__'

    create_func: _CreateFuncType
    scope_func: _ScopeFuncType
    registry: _RegistryType
    destructor_method_name: Optional[str]

    def __init__(self, create_func: _CreateFuncType, scope_func: _ScopeFuncType, destructor_method_name: Optional[str] = None):
        self.create_func = create_func
        self.scope_func = scope_func
        self.registry = {}
        self.destructor_method_name = destructor_method_name

    @property
    def generic_type(self) -> Type[_T]:
        try:
            return get_args(self.__orig_class__)[0]
        except (AttributeError, IndexError) as e:
            raise TypeError('Cannot determine generic type parameter') from e

    def get(self) -> Optional[_T]:
        try:
            key = self.scope_func()
            return self.registry[key]
        except Exception:  # noqa: BLE001
            return None

    def _set(self, **kwargs: Any) -> tuple[_ScopeType, Union[_T, Awaitable[_T]]]:
        key = self.scope_func()
        if key in self.registry:
            return key, self.registry[key]
        return key, self.create_func(**kwargs)

    def sync_set(self, **kwargs: Any) -> _T:
        key, result = self._set(**kwargs)
        if inspect.isawaitable(result):
            raise TypeError('create_func returned an awaitable; use async_set instead')
        self.registry[key] = result
        return result

    async def async_set(self, **kwargs: Any) -> _T:
        key, result = self._set(**kwargs)
        self.registry[key] = await result if inspect.isawaitable(result) else result
        return self.registry[key]

    def _clear(self, *scopes: _ScopeType):
        if not scopes and (scope := self.scope_func()):
            scopes = (scope,)

        if not (self.registry and scopes):
            return

        for scope in scopes:
            if scope in self.registry:
                instance = self.registry.pop(scope)

                if isinstance(self.destructor_method_name, str):
                    destructor_method = getattr(instance, self.destructor_method_name, None)
                    if destructor_method:
                        yield destructor_method()

    def sync_clear(self, *scopes: _ScopeType) -> None:
        for result in self._clear(*scopes):
            if inspect.isawaitable(result):
                raise TypeError('destructor returned an awaitable; use async clear instead')

    async def async_clear(self, *scopes: _ScopeType) -> None:
        for result in self._clear(*scopes):
            if inspect.isawaitable(result):
                await result

    # deprecated: use async_set / async_clear instead

    async def __call__(self, **kwargs: Any) -> _T:
        return await self.async_set(**kwargs)

    async def clear(self, *scopes: _ScopeType) -> None:
        await self.async_clear(*scopes)
