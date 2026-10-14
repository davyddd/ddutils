from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from types import NoneType
from typing import Any
from uuid import UUID

from ddutils.annotation_helpers import NON_COMPLEX_SEQUENCE_TYPES

# The order matters, a value is matched against the first type it is an instance of:
# `bool` is a subclass of `int`, `datetime` is a subclass of `date`
BASE_VALUE_TYPES = (NoneType, bool, int, float, str, bytes, bytearray, datetime, date, time, timedelta, UUID, Decimal)


def unwrap_enum(value: Any) -> Any:
    """Return the `.value` of an `Enum` member, any other value as is."""
    return value.value if isinstance(value, Enum) else value


def get_base_value_type(value: Any) -> type:
    """
    Return the base value type a value should be treated as, looking past subclasses: one of `BASE_VALUE_TYPES`
    (`NoneType`, `bool`, `int`, `float`, `str`, `bytes`, `bytearray`, `datetime`, `date`, `time`, `timedelta`, `UUID`,
    `Decimal`). An `Enum` member is looked at through its `.value`. Raises `TypeError` for any other value.
    """
    value = unwrap_enum(value)
    for base_type in BASE_VALUE_TYPES:
        if isinstance(value, base_type):
            return base_type

    raise TypeError(f'Value of type `{type(value).__name__}` has no base value type')


def is_complex_sequence_value(value: Any) -> bool:
    """Return whether a value is a sequence other than `str`, `bytes` or `bytearray`; subclasses are handled."""
    return isinstance(value, Sequence) and not isinstance(value, NON_COMPLEX_SEQUENCE_TYPES)
