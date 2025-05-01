import inspect
from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict, Generic, Hashable, TypeVar, Union

_T = TypeVar('_T', bound=Any)
_CreateFuncType = Union[Callable[..., _T], Callable[..., Awaitable[_T]]]
_ScopeType = Hashable
_ScopeFuncType = Callable[[], _ScopeType]
_RegistryType = Dict[_ScopeType, _T]


class ScopedRegistry(Generic[_T]):
    __slots__ = 'create_func', 'scope_func', 'registry'

    create_func: _CreateFuncType
    scope_func: _ScopeFuncType
    registry: _RegistryType

    def __init__(self, create_func: _CreateFuncType, scope_func: _ScopeFuncType):
        self.create_func = create_func
        self.scope_func = scope_func
        self.registry = {}

    async def __call__(self, **kwargs: Any) -> _T:
        key = self.scope_func()
        if key not in self.registry:
            value: _T
            result: Any = self.create_func(**kwargs)
            if inspect.isawaitable(result):
                value = await result
            else:
                value = result

            self.registry[key] = value
            return value

        return self.registry[key]

    def get(self) -> _T | None:
        try:
            key = self.scope_func()
            return self.registry[key]
        except Exception:  # noqa: BLE001
            return None

    def clear(self) -> None:
        with suppress(KeyError):
            del self.registry[self.scope_func()]
