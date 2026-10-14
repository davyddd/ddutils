import inspect
from collections.abc import Sequence
from types import UnionType
from typing import Any, Union, get_args, get_origin

NON_COMPLEX_SEQUENCE_TYPES = (str, bytes, bytearray)


def get_annotation_origin(annotation: Any) -> Any:
    if annotation is None:
        return annotation
    elif hasattr(annotation, '__origin__'):
        # This is a generic type from the typing module
        # Generic types like List[int], Dict[str, int] have an '__origin__' attribute
        return get_annotation_origin(annotation.__origin__)
    elif hasattr(annotation, '__supertype__'):
        # This is a type created with NewType
        return get_annotation_origin(annotation.__supertype__)
    elif annotation is Union or isinstance(annotation, UnionType):
        # This also includes Optional types, since Optional[T] is Union[T, None]
        raise TypeError('Union types are not supported')
    elif not isinstance(annotation, type):
        raise TypeError('Annotation must be instance of type')

    return annotation


def is_subclass(annotation: Any, *base_types: Any) -> bool:
    annotation_origin = get_annotation_origin(annotation)
    return inspect.isclass(annotation_origin) and issubclass(
        annotation_origin, tuple(get_annotation_origin(base_type) for base_type in base_types)
    )


def is_complex_sequence(annotation: Any) -> bool:
    annotation_origin = get_annotation_origin(annotation)
    return not is_subclass(annotation_origin, *NON_COMPLEX_SEQUENCE_TYPES) and is_subclass(annotation_origin, Sequence)


def get_complex_sequence_element_annotation(annotation: Any) -> Any:
    if hasattr(annotation, '__supertype__'):
        return get_complex_sequence_element_annotation(annotation.__supertype__)
    elif not is_complex_sequence(annotation):
        raise ValueError('Annotation must be a complex sequence')

    element_annotation = next(iter(get_args(annotation)), None)
    if element_annotation is None:
        raise ValueError('Annotation must have subtype')

    return element_annotation


def get_dict_items_annotation(annotation: Any) -> tuple[Any, Any]:
    if hasattr(annotation, '__supertype__'):
        return get_dict_items_annotation(annotation.__supertype__)
    elif not is_subclass(annotation, dict):
        raise TypeError('`annotation` must be a dict')

    annotation_args = get_args(annotation)
    if len(annotation_args) != 2:  # noqa: PLR2004
        raise ValueError('Dict annotation must have two arguments')

    key_annotation, value_annotation = annotation_args

    return key_annotation, value_annotation


def get_annotation_without_optional(annotation: Any) -> Any:
    try:
        get_annotation_origin(annotation)
        return annotation
    except TypeError:
        annotation_args = tuple(arg for arg in get_args(annotation) if arg is not type(None))

        if len(annotation_args) != 1:  # noqa: PLR2004
            raise TypeError('Union types are not supported') from None

        return annotation_args[0]


def _join_annotation_names(items: Any, separator: str) -> str:
    return separator.join(get_annotation_name(item) for item in items)


def get_annotation_name(annotation: Any) -> str:
    """
    Return a readable name of an annotation for messages: `int`, `int | float`, `list[int]`, `None`.

    Accepts a class, a union (`int | None`, `Optional[int]`, `Union[int, str]`), a generic (`dict[str, int]`,
    `Literal['a', 'b']`) or a tuple of classes as `isinstance` takes it, and renders them the way they are written.
    """
    if annotation is None or annotation is type(None):
        return 'None'
    if annotation is Ellipsis:
        return '...'
    if isinstance(annotation, (str, bytes, int, float)):  # a `Literal` value
        return repr(annotation)
    if isinstance(annotation, tuple):
        return _join_annotation_names(annotation, ' | ')
    if isinstance(annotation, UnionType) or get_origin(annotation) is Union:
        return _join_annotation_names(get_args(annotation), ' | ')
    if isinstance(annotation, list):  # the parameters of a `Callable`
        return f'[{_join_annotation_names(annotation, ", ")}]'
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is not None and args:
        return f'{get_annotation_name(origin)}[{_join_annotation_names(args, ", ")}]'
    if isinstance(annotation, type):
        return annotation.__name__
    return str(annotation).replace('typing.', '')
