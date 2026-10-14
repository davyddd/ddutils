from collections.abc import Sequence
from enum import Enum
from typing import Any

from ddutils.annotation_helpers import NON_COMPLEX_SEQUENCE_TYPES

# `bool` goes before `int` because `bool` is a subclass of `int`
BUILTIN_BASE_TYPES = (bool, int, float, str, bytes)


def unwrap_enum(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def get_builtin_base_type(value: Any) -> type:
    """
    Return the builtin type a value should be treated as, looking past subclasses: `bool`, `int`, `float`, `str`
    or `bytes`. An `Enum` member is looked at through its `.value`. Raises `TypeError` for any other value.
    """
    value = unwrap_enum(value)
    for base_type in BUILTIN_BASE_TYPES:
        if isinstance(value, base_type):
            return base_type

    raise TypeError(f'Value of type `{type(value).__name__}` has no builtin base type')


def is_complex_sequence_value(value: Any) -> bool:
    """Return whether a value is a sequence other than `str`, `bytes` or `bytearray`; subclasses are handled."""
    return isinstance(value, Sequence) and not isinstance(value, NON_COMPLEX_SEQUENCE_TYPES)
