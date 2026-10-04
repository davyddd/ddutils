import inspect
from collections.abc import Callable
from typing import Any, TypeVar, get_args, get_origin

_T = TypeVar('_T', bound=Any)


def get_origin_class_of_method(cls: Any, method_name: str) -> type | None:
    """
    Find the class in the inheritance hierarchy where a method is originally defined.

    This function traverses the Method Resolution Order (MRO) of the given class
    to find the first class that defines the specified method in its own namespace.

    Args:
        cls: The class to inspect.
        method_name: The name of the method to locate.

    Returns:
        The class in which the method is originally defined, or None if the method is not found.
    """
    for base in inspect.getmro(cls):
        if method_name in base.__dict__:
            return base
    return None


def get_generic_base_argument(cls: type, generic_base: type, position: int = 0) -> Any | None:
    """
    Return the type argument that `cls` bound to `generic_base` when subclassing it.

    For `class ProfileCache(GenericCache[Profile])` this is `Profile`. Returns `None` when `cls` does not
    subscript `generic_base` (`class Cache(GenericCache)`), and a `TypeVar` when the subclass is still
    generic (`class Base[T](GenericCache[T])`), so callers can reject both cases in `__init_subclass__`.

    Args:
        cls: The class to inspect.
        generic_base: The generic base class whose argument to look up.
        position: Index of the argument for bases with several type parameters.
    """
    for base in getattr(cls, '__orig_bases__', ()):
        if get_origin(base) is generic_base:
            arguments = get_args(base)
            return arguments[position] if position < len(arguments) else None
    return None


class classproperty:  # noqa: N801
    """
    A descriptor that defines a read-only property at the class level.

    Similar to the built-in @property decorator, but applies to the class itself rather than instances.
    Allows access to computed values directly from the class without creating an instance.

    Example:
        class MyClass:
            @classproperty
            def class_name(cls):
                return cls.__name__

        # Access without instantiation
        name = MyClass.class_name
    """

    def __init__(self, fget: Callable[..., Any]) -> None:
        """
        Initialize the classproperty with a class-level getter function.

        Args:
            fget: A class-level getter function that takes the owning class as its only argument.
        """
        self.fget = fget
        self.__doc__ = fget.__doc__
        self.__name__ = getattr(fget, '__name__', type(fget).__name__)

    def __get__(self, instance: Any, owner: type[Any]) -> Any:
        """
        Retrieve the property value using the descriptor protocol.

        Args:
            instance: The instance accessing the property (can be None when accessed via the class).
            owner: The class that owns this property.

        Returns:
            The value returned by the getter function when called with the owner class.
        """
        return self.fget(owner)
