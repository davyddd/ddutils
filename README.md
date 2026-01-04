# DDUtils

[![pypi](https://img.shields.io/pypi/v/ddutils.svg)](https://pypi.python.org/pypi/ddutils)
[![downloads](https://static.pepy.tech/badge/ddutils/month)](https://pepy.tech/project/ddutils)
[![versions](https://img.shields.io/pypi/pyversions/ddutils.svg)](https://github.com/davyddd/ddutils)
[![codecov](https://codecov.io/gh/davyddd/ddutils/branch/main/graph/badge.svg)](https://app.codecov.io/github/davyddd/ddutils)
[![license](https://img.shields.io/github/license/davyddd/ddutils.svg)](https://github.com/davyddd/ddutils/blob/main/LICENSE)

**DDUtils** is a lightweight Python library that provides helper functions and decorators for common programming tasks.
It focuses on type safety, robustness, and runtime introspection — all without external dependencies.

## Installation

Install the library using pip:
```bash
pip install ddutils
```

## Type Annotation Helpers

Utilities for inspecting and working with Python type hints and generic types.
These helpers let you analyze and modify complex annotations at runtime.

### get_annotation_origin

Returns the base (origin) type of a generic annotation, unwrapping `NewType` and handling generic aliases recursively.

```python
from typing import List
from ddutils.annotation_helpers import get_annotation_origin


get_annotation_origin(List[int])  # <class 'list'>
get_annotation_origin(dict[str, int])  # <class 'dict'>
```

### is_subclass

Checks whether a type annotation is a subclass of the given base type(s).
Supports both regular and generic annotations, following standard `issubclass` behavior.

```python
from typing import List
from ddutils.annotation_helpers import is_subclass


is_subclass(List[int], list)  # True
is_subclass(dict[str, int], dict)  # True
is_subclass(List[str], dict)  # False
```

### is_complex_sequence

Checks whether a type annotation represents a sequence type, excluding `str`, `bytes`, and `bytearray`.

```python
from typing import List, Tuple
from ddutils.annotation_helpers import is_complex_sequence


is_complex_sequence(List[int])  # True
is_complex_sequence(Tuple[str, ...])  # True
is_complex_sequence(str)  # False
is_complex_sequence(dict)  # False
```

### get_complex_sequence_element_annotation

Returns the element type from a sequence annotation.
Raises `ValueError` if the annotation doesn’t specify an element type.

```python
from typing import List, Set
from ddutils.annotation_helpers import get_complex_sequence_element_annotation


get_complex_sequence_element_annotation(List[int])  # <class 'int'>
get_complex_sequence_element_annotation(Set[str])  # <class 'str'>
```

### get_dict_items_annotation

Returns the key and value types from a dictionary annotation.

```python
from typing import Dict
from ddutils.annotation_helpers import get_dict_items_annotation


key_type, value_type = get_dict_items_annotation(Dict[str, int])
# key_type = <class 'str'>, value_type = <class 'int'>
```

### get_annotation_without_optional

Returns a type annotation without its `Optional` wrapper, extracting the underlying type from `Union[T, None]`.
Raises `TypeError` for unions that include multiple non-None types.

```python
from typing import Optional
from ddutils.annotation_helpers import get_annotation_without_optional


get_annotation_without_optional(Optional[int])  # <class 'int'>
get_annotation_without_optional(Optional[List[str]])  # typing.List[str]
```

## Class Helpers

Helper functions for inspecting and extending class-level behavior

### classproperty

Works like `@property`, but for class attributes.
Can be accessed as `ClassName.property_name` without creating an instance.

```python
from ddutils.class_helpers import classproperty


class BaseModel:
    @classproperty
    def table_name(cls):
        return f'{cls.__name__.lower()}_table'


class User(BaseModel):
    pass


User.table_name  # 'user_table'
```

### get_origin_class_of_method

Traverses the Method Resolution Order (MRO) to find the class where a method was originally defined. 
Returns `None` if the method doesn’t exist.

```python
from ddutils.class_helpers import get_origin_class_of_method


class A:
    def method(self):
        pass


class B(A):
    pass


class C(B):
    def method(self):
        pass


get_origin_class_of_method(C, 'method')  # <class 'C'>
get_origin_class_of_method(B, 'method')  # <class 'A'>
```

## Function Helpers

Tools for creating and modifying Python functions at runtime.

### create_new_function

Creates a new function from an existing one, with an optional new name. 
Preserves default values and closures.

```python
from ddutils.function_helpers import create_new_function


def original_function():
    return 'original'


new_function = create_new_function(original_function, new_name='renamed_function')
new_function.__name__  # 'renamed_function'
```

## Data Conversion

Helpers for converting data between different formats.

### convert_camel_case_to_snake_case

Converts a camelCase string to snake_case.

```python
from ddutils.convertors import convert_camel_case_to_snake_case


convert_camel_case_to_snake_case('SomeClassName')  # 'some_class_name'
```

### convert_to_repr

Builds a `__repr__` string for objects that have a `__dict__`.
Ignores private attributes and raises `TypeError` if the object doesn’t have `__dict__`.

```python
from ddutils.convertors import convert_to_repr


class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        self._internal = 'hidden'


person = Person('Alice', 30)
convert_to_repr(person)  # "Person(name='Alice', age=30)"
```

### convert_timedelta_to_milliseconds

Converts `timedelta` objects to milliseconds as an integer.

```python
from datetime import timedelta
from ddutils.convertors import convert_timedelta_to_milliseconds


delta = timedelta(seconds=5, milliseconds=500)
convert_timedelta_to_milliseconds(delta)  # 5500
```

## Datetime Helpers

Utilities for working with dates and times.

### utc_now

Returns the current datetime in UTC timezone.

## Safe Decorators

Decorators that help functions fail safely and handle exceptions gracefully.

### safe_call

Wraps a function to catch exceptions and return a default value instead of raising errors.

```python
import requests
from ddutils.safe_decorators import safe_call


@safe_call(default_result=[])
def fetch_data_from_api():
    response = requests.get('https://api.example.com/data')
    return response.json()


@safe_call(default_result=0, exceptions=(ValueError,))
def convert_to_int(value):
    return int(value)
```

### retry_once_after_exception

Retries a function once if it raises an exception.

```python
import requests
from ddutils.safe_decorators import retry_once_after_exception


@retry_once_after_exception
def unstable_network_call():
    return requests.get('https://api.example.com/unstable')
```

## Module and Object Management

Helpers for importing and accessing modules or objects at runtime.

### get_module

Finds a nested module by path within a parent module.

```python
import os
from ddutils.module_getter import get_module


get_module(os, ['path'])  # <module 'os.path'>
```

### get_object_by_path

Imports and returns an object by its full dotted path (e.g. 'json.loads').

```python
from ddutils.object_getter import get_object_by_path


json_loads = get_object_by_path('json.loads')
```

## Scoped Registry

A registry that manages object instances within defined scopes.

### ScopedRegistry

Manages object instances within scopes (like per request or per session).

```python
from ddutils.scoped_registry import ScopedRegistry


def get_current_request_id(): ...


def create_database_connection(): ...


db_registry = ScopedRegistry(
    create_func=create_database_connection,
    scope_func=get_current_request_id,
)


async def handle_request():
    db = await db_registry()  # Returns existing or creates new db connection
    await db.execute('select ...')
```

## Function Exception Extraction

AST-based introspection for extracting exceptions from function source code.

### extract_function_exceptions

Parses a function’s source code to find all `raise` statements and identify the exception types they use. 
Returns an iterator of `ExceptionInfo` objects describing each raised exception.

## Sequence Helpers

Safe operations on sequence types.

### get_safe_element

Returns an element from a sequence by index without raising `IndexError`.
Returns `None` if the index is out of range.

```python
from ddutils.sequence_helpers import get_safe_element


items = [1, 2, 3]
get_safe_element(items, 0)   # 1
get_safe_element(items, 10)  # None (no IndexError)
get_safe_element(items, -1)  # 3
```
