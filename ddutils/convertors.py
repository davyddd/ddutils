from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import NoneType
from typing import Any, Protocol
from uuid import UUID

from ddutils.value_helpers import BASE_VALUE_TYPES, get_base_value_type, unwrap_enum


class ClassInstanceWithDict(Protocol):
    __dict__: dict


def convert_camel_case_to_snake_case(string: str) -> str:
    return ''.join(f'_{char.lower()}' if char.isupper() else char for char in string).lstrip('_')


def convert_to_repr(obj: ClassInstanceWithDict) -> str:
    class_name = obj.__class__.__name__
    if not hasattr(obj, '__dict__'):
        raise TypeError(f'Instance of {class_name} class does not have a `__dict__` attribute.')

    attrs = ', '.join(f'{key}={value!r}' for key, value in obj.__dict__.items() if not key.startswith('_'))
    return f'{class_name}({attrs})'


def convert_timedelta_to_milliseconds(delta: timedelta) -> int:
    return int(delta.total_seconds() * 1000)


def _convert_to_datetime(value: datetime) -> datetime:
    return datetime(
        value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond,
        value.tzinfo, fold=value.fold,
    )  # fmt: skip


def _convert_to_date(value: date) -> date:
    return date(value.year, value.month, value.day)


def _convert_to_time(value: time) -> time:
    return time(value.hour, value.minute, value.second, value.microsecond, value.tzinfo, fold=value.fold)


def _convert_to_timedelta(value: timedelta) -> timedelta:
    # not `total_seconds()`: it goes through a float and loses microseconds on large values
    return timedelta(days=value.days, seconds=value.seconds, microseconds=value.microseconds)


def _convert_to_uuid(value: UUID) -> UUID:
    return UUID(int=value.int)


# A cast for every type of `BASE_VALUE_TYPES`: the constructor where it accepts an instance of a subclass,
# a function building the value from its fields otherwise
BASE_VALUE_CONVERTORS: dict[type, Callable[[Any], Any]] = {
    NoneType: lambda _: None,
    bool: bool,
    int: int,
    float: float,
    str: str,
    bytes: bytes,
    bytearray: bytearray,
    datetime: _convert_to_datetime,
    date: _convert_to_date,
    time: _convert_to_time,
    timedelta: _convert_to_timedelta,
    UUID: _convert_to_uuid,
    Decimal: Decimal,
}

if set(BASE_VALUE_CONVERTORS) != set(BASE_VALUE_TYPES):
    raise RuntimeError('`BASE_VALUE_CONVERTORS` must define a convertor for exactly the types of `BASE_VALUE_TYPES`')


def convert_to_base_value(value: Any) -> Any:
    """
    Cast a value to its base value type (see `get_base_value_type`): a `str` subclass becomes a plain `str`,
    a `UUID` subclass a plain `UUID`, a `datetime` subclass a plain `datetime` with the same `tzinfo` and `fold`,
    an `Enum` member becomes its `.value` cast the same way, `None` stays `None`.
    Raises `TypeError` for a value without a base type.
    """
    value = unwrap_enum(value)
    return BASE_VALUE_CONVERTORS[get_base_value_type(value)](value)
