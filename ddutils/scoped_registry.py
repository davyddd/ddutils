import inspect
from typing import Any, Awaitable, Callable, Dict, Generic, Hashable, TypeVar, Union

_T = TypeVar('_T', bound=Any)
_CreateFuncType = Union[Callable[..., _T], Callable[..., Awaitable[_T]]]
_ScopeType = Hashable
_ScopeFuncType = Callable[[], _ScopeType]
_RegistryType = Dict[_ScopeType, _T]

# A method must not have any attributes.
# The count is shown as 1 because the method’s `__annotations__` always includes the `return` type.
ALLOWED_AMOUNT_METHOD_ATTRIBUTES = 1


class ScopedRegistry(Generic[_T]):
    __slots__ = 'create_func', 'scope_func', 'registry', 'destructor_method_name'

    create_func: _CreateFuncType
    scope_func: _ScopeFuncType
    registry: _RegistryType
    destructor_method_name: str | None

    def __init__(self, create_func: _CreateFuncType, scope_func: _ScopeFuncType, destructor_method_name: str | None = None):
        self.create_func = create_func
        self.scope_func = scope_func
        self.registry = {}
        self.destructor_method_name = destructor_method_name

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

    async def clear(self, *scopes: _ScopeType) -> None:
        if not scopes and (scope := self.scope_func()):
            scopes = (scope,)

        if not (self.registry and scopes):
            return

        for scope in scopes:
            if scope in self.registry:
                instance = self.registry.pop(scope)

                if isinstance(self.destructor_method_name, str):
                    destructor_method = getattr(instance, self.destructor_method_name, None)
                    if destructor_method and len(destructor_method.__annotations__) == ALLOWED_AMOUNT_METHOD_ATTRIBUTES:
                        result: Any = destructor_method()
                        if inspect.isawaitable(result):
                            await result
