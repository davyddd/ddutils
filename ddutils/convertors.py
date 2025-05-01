from datetime import timedelta
from typing import Protocol


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
