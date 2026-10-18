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

## Development

The project runs entirely in Docker. Requires Docker and [Fabric](https://www.fabfile.org/) on the host:

```bash
fab build      # build the dev image
fab tests      # run pytest
fab linters    # run ruff (with --fix), ty and complexipy
fab shell      # IPython inside the container
fab bash       # bash inside the container
```

This project was generated from [dd-lib-stub](https://github.com/davyddd/dd-lib-stub);
run `uvx copier update` to pull in template updates.

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

Checks whether a type annotation represents a sequence type, excluding `str`, `bytes`, and `bytearray`
and their subclasses (a `str`-based `Enum` is not a complex sequence).

```python
from enum import Enum
from typing import List, Tuple
from ddutils.annotation_helpers import is_complex_sequence


class Kind(str, Enum):
    A = 'a'


is_complex_sequence(List[int])  # True
is_complex_sequence(Tuple[str, ...])  # True
is_complex_sequence(str)  # False
is_complex_sequence(Kind)  # False
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

### get_annotation_name

Returns a readable name of an annotation for error messages: a class, a union or a tuple of classes as
`isinstance` takes it.

```python
from ddutils.annotation_helpers import get_annotation_name


get_annotation_name(int)            # 'int'
get_annotation_name((int, float))   # 'int | float'
get_annotation_name(int | None)     # 'int | None'
get_annotation_name(list[int])      # 'list[int]'
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

### get_generic_base_argument

Returns the type argument a class bound to a generic base when subclassing it. `None` when the base was not
subscripted, the `TypeVar` itself when the subclass is still generic.

```python
from typing import Generic, TypeVar

from ddutils.class_helpers import get_generic_base_argument

T = TypeVar('T')


class Repository(Generic[T]):
    pass


class UserRepository(Repository[User]):
    pass


get_generic_base_argument(UserRepository, Repository)  # <class 'User'>
get_generic_base_argument(Repository, Repository)      # None
```

### require_class_attribute

Returns a class attribute that subclasses are expected to declare, for `__init_subclass__` checks. A missing,
`None` or empty value raises `AttributeError`, a value of the wrong type raises `TypeError`; both name the
attribute and the class, so a misconfigured subclass fails at definition rather than on first use.

```python
from typing import ClassVar

from ddutils.class_helpers import require_class_attribute


class BaseConsumer:
    topic: ClassVar[str]
    batch_size: ClassVar[int] = 100

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        require_class_attribute(cls, 'topic', str)
        require_class_attribute(cls, 'batch_size', int)


class EventConsumer(BaseConsumer):
    topic = 'events'


class BrokenConsumer(BaseConsumer):  # AttributeError: `topic` class attribute of BrokenConsumer must be set
    pass
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

### convert_to_base_value

Casts a value to its base value type (see [get_base_value_type](#get_base_value_type)):
a `str` subclass becomes a plain `str`, a `UUID` subclass a plain `UUID`, a `datetime` subclass a plain `datetime`
with the same `tzinfo` and `fold`, an `Enum` member becomes its `.value` cast the same way, `None` stays `None`.
Raises `TypeError` for a value without a base type.

Normalize a value once, then dispatch on the result with plain `isinstance` checks: subclasses, `Enum` members
and third-party types such as a `pendulum.DateTime` all land on the stdlib type.

```python
from enum import Enum
from uuid import UUID
from ddutils.convertors import convert_to_base_value


class Kind(str, Enum):
    A = 'a'


class ProfileId(UUID):
    pass


convert_to_base_value(None)  # None
convert_to_base_value(Kind.A)  # 'a' (not 'Kind.A', which `str(Kind.A)` would give)
convert_to_base_value(ProfileId('12345678-1234-5678-1234-567812345678'))  # UUID('1234...'), exact type UUID
convert_to_base_value(object())  # TypeError
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

A registry that keeps one object instance per scope and manages its lifetime.

### ScopedRegistry

Keeps one object per scope. `scope_func` decides what the current scope is and returns its key; `None` means
"no current scope" and makes every method raise `RuntimeError`.

`scope()` is the entry point into a scope: it creates the object on enter and removes it on exit, calling
the optional destructor exactly once. Nested `scope()` blocks join the existing object and leave it alone.
Concurrent first accesses with the same key call `create_func` only once.

```python
import asyncio

from ddutils.scoped_registry import ScopedRegistry


async def create_session(): ...


# One session per task: a child task spawned with gather/create_task gets its own session
session_registry = ScopedRegistry(create_func=create_session, scope_func=asyncio.current_task, destructor_method_name='close')


async def handle_request():
    async with session_registry.scope() as session:  # created here, closed and removed on exit
        await session.execute('select ...')
        async with session_registry.scope() as same_session:  # nested block joins
            ...
```

Lower-level methods are available when a context manager does not fit:

- `get()` returns the current object or `None`;
- `set(**kwargs)` returns the existing object or creates it. Whoever calls it takes over the cleanup that
  `scope()` does on exit and must call `clear()` when the object is no longer needed, if it ever is: a
  per-process client may live until the process ends;
- `clear()` removes the object of the current scope and calls the destructor.

#### Scopes kept in a ContextVar

A `scope_func` that declares a `token` parameter receives a freshly generated token when `scope()` is entered
and `None` on every other access. This is for a scope of one execution (an HTTP request, an actor run) rather
than one task: the function stores the token in a `ContextVar`, so coroutines spawned inside the block
(`gather`, `TaskGroup`, `create_task`) inherit it and share the object with the parent, while outside of
`scope()` there is no key and every method raises.

```python
from contextvars import ContextVar

execution_key: ContextVar[str | None] = ContextVar('execution_key', default=None)


def execution_scope(token: str | None) -> str | None:
    key = execution_key.get()
    if key is None and token is not None:  # entering scope() outside of an execution: start one
        execution_key.set(token)
        key = token
    return key


async def create_log_properties(**kwargs): ...


log_registry = ScopedRegistry(create_func=create_log_properties, scope_func=execution_scope)


async def middleware(headers):
    async with log_registry.scope(headers=headers) as log_properties:
        await asyncio.gather(work(), work())  # both see the same log_properties via log_registry.get()
```

Reads never start a scope: a `get()` from a long-living context (a startup log in the server's main task)
that planted a key would be inherited by every request task, making all requests share one object. For the
same reason the key is not reset when the block ends, so `scope()` must be entered in a task that does not
outlive the block (a request handler, an actor run).

## Connections

`ddutils.connections` sits between a `ScopedRegistry` and the code that uses a connection: a query, a cache
lookup, a Kafka send. A registry holds one connection per scope: a pooled client per process, a session
per task. The connections module adds two things on top:

- `ConnectionManagerFactory(registries, default, connection_manager_class=ConnectionManager)` resolves a
  connection alias to its registry, like Django's `using`. Calling it opens a connection manager on the
  chosen registry; `registry(alias)` returns the registry itself; `close()` clears every registry for the
  current scope, calling the connection's destructor, which is the shutdown hook of process-scoped clients.
- `ConnectionManager(registry)` is the default connection manager: an async context manager that hands out
  the connection of the registry's current scope and releases nothing on exit. Enough for clients that are
  pools themselves, such as ClickHouse, Redis or a Kafka producer.

Databases with transactions pass their own `connection_manager_class`: a unit of work that begins, commits
or rolls back and closes the session on exit. It depends on the driver, so it lives in the project.

```python
import os
from enum import Enum

from ddutils.connections import ConnectionManagerFactory
from ddutils.scoped_registry import ScopedRegistry


class ClickhouseDB(str, Enum):
    PRIMARY = 'primary'


client_registries = {
    db: ScopedRegistry(create_func=make_client_for(db), scope_func=os.getpid, destructor_method_name='close')
    for db in ClickhouseDB
}
clickhouse = ConnectionManagerFactory(client_registries, default=ClickhouseDB.PRIMARY)


async with clickhouse() as client:
    result = await client.query(sql)


# a transactional database: `Atomic` is your unit of work over `registry.scope()`
atomic = ConnectionManagerFactory(session_registries, default=PostgresDB.PRIMARY, connection_manager_class=Atomic)


async with atomic(alias=PostgresDB.REPLICA) as session:
    ...


# on shutdown: closes the clients of every alias that was used in this process
await clickhouse.close()
```

## Feature Flags

`ddutils.feature_flags` is the storage-agnostic part of feature flags: `FeatureFlagRecord` (on or off, the proportion
of readers that see it, a free-form payload), the `FeatureFlagStorage` interface and `FeatureFlags`, which reads
through a storage with a per-process cache (`BASE_TTL` plus a random jitter). While the storage fails, the last
known record is served and re-read with an exponential backoff from `ERROR_TTL` up to the TTL. The storages live
with their clients: `ddredis.feature_flags.RedisFeatureFlagStorage`, `ddaerospike.feature_flags.AerospikeFeatureFlagStorage`.

Readers see booleans and payloads, not records. `is_enabled` is the flag's switch and its proportion in one answer:
off for everyone when the flag is off, on for the `proportion` of the readers when it is on, so a kill-switch is a
flag with proportion 1.0. With an `idempotent_key` (a user id, an account id) the split is repeatable, the same
user always lands on the same side; without one it is random per call. `get_payload` is the payload as stored; its shape is the application's,
parse it there.

```python
from ddredis.feature_flags import RedisFeatureFlagStorage
from ddutils.feature_flags import FeatureFlags

feature_flags = FeatureFlags(RedisFeatureFlagStorage(redis_client_factory))

# a kill-switch: proportion 1.0, on or off for everyone
if await feature_flags.is_enabled('new_checkout'):
    ...

# a gradual rollout: on for `proportion` of the users, the same users every time
if await feature_flags.is_enabled('new_ranking', user_id):
    ...

# a kill-switch with settings
if await feature_flags.is_enabled('email_provider_block'):
    rules = EmailProviderBlockRules.model_validate(await feature_flags.get_payload('email_provider_block'))
```

A storage implements `get`, `get_map`, `put` and `delete`; `rename` defaults to
put-then-delete and is overridden where the storage can do it atomically. `FeatureFlagRecord` validates itself on
construction; a storage builds it with `from_dict` and, when what it read is not a valid record, logs it and reads
it as the defaults. A storage failure raises `FeatureFlagStorageError`
with the cause chained.

## Context Helpers

### async_suppress

`contextlib.suppress` as an async context manager, so it can share one `async with` with other async context
managers instead of nesting a sync `with` inside. Swallows only the listed exceptions raised inside the block.

```python
from ddredis.lock import AlreadyAcquiredError, RedisLock
from ddutils.context_helpers import async_suppress

async with async_suppress(AlreadyAcquiredError), RedisLock(redis_client_factory, 'sync-profiles', timeout=30):
    await sync_profiles()  # skipped when another worker holds the lock
```

## Function Exception Extraction

AST-based introspection for extracting exceptions from function source code.

### extract_function_exceptions

Parses a function’s source code to find all `raise` statements and identify the exception types they use. 
Returns an iterator of `ExceptionInfo` objects describing each raised exception.

## Value Helpers

Runtime counterparts of the annotation helpers: they inspect values, not type hints.

### get_base_value_type

Returns the base value type a value should be treated as, looking past subclasses. The candidates, in order,
are `BASE_VALUE_TYPES`: `NoneType`, `bool`, `int`, `float`, `str`, `bytes`, `bytearray`, `datetime`, `date`, `time`,
`timedelta`, `UUID`, `Decimal` (`bool` is checked before `int`, `datetime` before `date`). An `Enum` member is looked at
through its `.value`. Raises `TypeError` for any other value, a collection or a mapping included. Useful for APIs that dispatch on the exact type
(serializers, query builders).

```python
from datetime import datetime
from enum import Enum
from uuid import UUID
from ddutils.value_helpers import get_base_value_type


class Kind(str, Enum):
    A = 'a'


class ProfileId(UUID):
    pass


get_base_value_type(None)  # <class 'NoneType'>
get_base_value_type(True)  # <class 'bool'>
get_base_value_type(Kind.A)  # <class 'str'>
get_base_value_type(ProfileId('12345678-1234-5678-1234-567812345678'))  # <class 'uuid.UUID'>
get_base_value_type(datetime.now())  # <class 'datetime.datetime'>
get_base_value_type(object())  # TypeError
```

### unwrap_enum

Returns the `.value` of an `Enum` member and any other value as is. `str(Kind.A)` of a `class Kind(str, Enum)`
is `'Kind.A'`, so a member has to be unwrapped before it is formatted or cast.

```python
from enum import Enum
from ddutils.value_helpers import unwrap_enum


class Kind(str, Enum):
    A = 'a'


unwrap_enum(Kind.A)  # 'a'
unwrap_enum('a')  # 'a'
```

### is_complex_sequence_value

Checks whether a value is a sequence other than `str`, `bytes` or `bytearray` (subclasses included).
Sets and mappings are not sequences. The runtime counterpart of [is_complex_sequence](#is_complex_sequence).

```python
from ddutils.value_helpers import is_complex_sequence_value


is_complex_sequence_value([1, 2])  # True
is_complex_sequence_value((1, 2))  # True
is_complex_sequence_value('abc')  # False
is_complex_sequence_value({1, 2})  # False
```

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
