import asyncio
import os
import unittest
from contextvars import ContextVar

from parameterized import parameterized

from ddutils.scoped_registry import ScopedRegistry


class Resource:
    def __init__(self, name: str = 'resource'):
        self.name = name
        self.closed = 0

    def close(self) -> None:
        self.closed += 1

    async def aclose(self) -> None:
        self.closed += 1


def sync_create_func(**kwargs) -> Resource:
    return Resource(**kwargs)


async def async_create_func(**kwargs) -> Resource:
    return Resource(**kwargs)


def constant_scope_func() -> str:
    return 'scope'


def make_execution_scope_func():
    """One key per `scope()` block, kept in a ContextVar and inherited by tasks spawned inside the block."""
    execution_key: ContextVar[str | None] = ContextVar('execution_key', default=None)

    def execution_scope_func(token: str | None) -> str | None:
        key = execution_key.get()
        if key is None and token is not None:
            execution_key.set(token)
            key = token
        return key

    return execution_scope_func


class TestScopedRegistry(unittest.IsolatedAsyncioTestCase):
    @parameterized.expand((sync_create_func, async_create_func))
    def test_init(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act & Assert
        self.assertEqual(registry.create_func, func)
        self.assertEqual(registry.scope_func, constant_scope_func)
        self.assertEqual(registry.registry, {})
        self.assertEqual(registry.destructor_method_name, 'close')
        self.assertIsNone(registry.get())

    @parameterized.expand((sync_create_func, async_create_func))
    async def test_set(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func)

        # Act
        first = await registry.set(name='first')
        second = await registry.set(name='second')

        # Assert
        self.assertIs(first, second)
        self.assertEqual(first.name, 'first')
        self.assertIs(registry.get(), first)

    async def test_set_race(self):
        # Arrange
        calls = 0

        async def slow_create_func() -> Resource:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return Resource()

        registry = ScopedRegistry(create_func=slow_create_func, scope_func=constant_scope_func)

        # Act
        results = await asyncio.gather(*(registry.set() for _ in range(5)))

        # Assert
        self.assertEqual(calls, 1)
        self.assertEqual(len(registry.registry), 1)
        self.assertTrue(all(result is results[0] for result in results))

    @parameterized.expand((sync_create_func, async_create_func))
    async def test_clear_with_destructor(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func, destructor_method_name='close')
        resource = await registry.set()

        # Act
        await registry.clear()

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertIsNone(registry.get())
        self.assertEqual(registry.registry, {})

    async def test_clear_with_async_destructor(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='aclose')
        resource = await registry.set()

        # Act
        await registry.clear()

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_clear_affects_only_current_scope(self):
        # Arrange
        current = {'key': 'a'}
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=lambda: current['key'], destructor_method_name='close'
        )
        resource_a = await registry.set(name='a')
        current['key'] = 'b'
        resource_b = await registry.set(name='b')

        # Act
        await registry.clear()

        # Assert
        self.assertEqual(resource_a.closed, 0)
        self.assertEqual(resource_b.closed, 1)
        self.assertEqual(registry.registry, {'a': resource_a})

    async def test_clear_without_entries_does_nothing(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act & Assert
        await registry.clear()
        await registry.clear()
        self.assertEqual(registry.registry, {})

    def test_builtin_scope_func(self):
        # Arrange: builtins without an introspectable signature are called with no arguments
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=os.getpid)

        # Act & Assert
        self.assertEqual(registry.get(), None)
        self.assertEqual(registry._get_scope_key('ignored-token'), os.getpid())

    def test_generic_type(self):
        # Arrange
        registry = ScopedRegistry[Resource](create_func=sync_create_func, scope_func=constant_scope_func)

        # Act & Assert
        self.assertIs(registry.generic_type, Resource)

    def test_generic_type_raises_without_type_param(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func)

        # Act & Assert
        with self.assertRaises(TypeError):
            _ = registry.generic_type


class TestScopedRegistryScope(unittest.IsolatedAsyncioTestCase):
    @parameterized.expand((sync_create_func, async_create_func))
    async def test_scope_creates_and_removes(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act
        async with registry.scope(name='scoped') as resource:
            inside = registry.get()

        # Assert
        self.assertIs(inside, resource)
        self.assertEqual(resource.name, 'scoped')
        self.assertEqual(resource.closed, 1)
        self.assertIsNone(registry.get())
        self.assertEqual(registry.registry, {})

    async def test_scope_removes_on_exception(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act
        with self.assertRaises(ValueError):
            async with registry.scope() as resource:
                raise ValueError('boom')

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_scope_removes_on_cancellation(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')
        entered = asyncio.Event()
        resources: list[Resource] = []

        async def work():
            async with registry.scope() as resource:
                resources.append(resource)
                entered.set()
                await asyncio.sleep(60)

        task = asyncio.create_task(work())
        await entered.wait()

        # Act
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task

        # Assert
        self.assertEqual(resources[0].closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_nested_scope_joins(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act
        async with registry.scope() as outer:
            async with registry.scope() as inner:
                pass
            after_inner = registry.get()
            closed_after_inner = outer.closed

        # Assert
        self.assertIs(inner, outer)
        self.assertIs(after_inner, outer)
        self.assertEqual(closed_after_inner, 0)
        self.assertEqual(outer.closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_scope_with_task_scope_func_is_exclusive_to_the_task(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=asyncio.current_task, destructor_method_name='close')

        async def child():
            seen_by_child = registry.get()
            async with registry.scope() as own:
                return seen_by_child, own

        # Act
        async with registry.scope() as parent_resource:
            seen_by_child, child_resource = await asyncio.create_task(child())
            entries_after_child = len(registry.registry)

        # Assert
        self.assertIsNone(seen_by_child)
        self.assertIsNot(child_resource, parent_resource)
        self.assertEqual(child_resource.closed, 1)
        self.assertEqual(entries_after_child, 1)
        self.assertEqual(parent_resource.closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_scope_race(self):
        # Arrange
        calls = 0

        async def slow_create_func() -> Resource:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return Resource()

        registry = ScopedRegistry(create_func=slow_create_func, scope_func=constant_scope_func, destructor_method_name='close')
        # Every block must still be inside the scope when the others enter, otherwise a re-creation is legitimate
        barrier = asyncio.Barrier(5)

        async def work():
            async with registry.scope() as resource:
                await barrier.wait()
                return resource

        # Act
        results = await asyncio.gather(*(work() for _ in range(5)))

        # Assert
        self.assertEqual(calls, 1)
        self.assertTrue(all(result is results[0] for result in results))
        self.assertEqual(results[0].closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_execution_scope_is_inherited_by_child_tasks(self):
        # Arrange
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=make_execution_scope_func(), destructor_method_name='close'
        )

        async def child():
            return registry.get()

        async def request():
            async with registry.scope(name='request') as resource:
                gathered, *_ = await asyncio.gather(child(), child())
                created = await asyncio.create_task(child())
                async with registry.scope() as nested:
                    pass
                return resource, gathered, created, nested

        # Act
        resource, gathered, created, nested = await asyncio.create_task(request())

        # Assert
        self.assertEqual(resource.name, 'request')
        self.assertIs(gathered, resource)
        self.assertIs(created, resource)
        self.assertIs(nested, resource)
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})

    async def test_execution_scope_parallel_requests_get_distinct_values(self):
        # Arrange
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=make_execution_scope_func(), destructor_method_name='close'
        )

        async def request():
            async with registry.scope() as resource:
                await asyncio.sleep(0)
                return resource

        # Act
        first, second = await asyncio.gather(asyncio.create_task(request()), asyncio.create_task(request()))

        # Assert
        self.assertIsNot(first, second)
        self.assertEqual((first.closed, second.closed), (1, 1))
        self.assertEqual(registry.registry, {})

    async def test_execution_scope_reads_do_not_start_a_scope(self):
        # Arrange: a read before any scope (e.g. a startup log) must not plant a key that later tasks inherit
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=make_execution_scope_func(), destructor_method_name='close'
        )

        async def request():
            async with registry.scope() as resource:
                await asyncio.sleep(0)
                return resource

        # Act & Assert
        with self.assertRaises(RuntimeError):
            registry.get()
        with self.assertRaises(RuntimeError):
            await registry.clear()
        first, second = await asyncio.gather(asyncio.create_task(request()), asyncio.create_task(request()))
        self.assertIsNot(first, second)
        self.assertEqual(registry.registry, {})

    @parameterized.expand(((lambda: None,), (lambda: [],), (lambda: {},)))
    async def test_invalid_scope_key(self, scope_func):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=scope_func)

        # Act & Assert
        with self.assertRaises(RuntimeError):
            registry.get()
        with self.assertRaises(RuntimeError):
            await registry.set()
        with self.assertRaises(RuntimeError):
            async with registry.scope():
                pass
        with self.assertRaises(RuntimeError):
            await registry.clear()
        self.assertEqual(registry.registry, {})

    async def test_execution_scope_set_starts_a_scope_the_caller_must_clear(self):
        # Arrange
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=make_execution_scope_func(), destructor_method_name='close'
        )

        async def child():
            return registry.get()

        # Act
        resource = await registry.set()
        seen_by_child = await asyncio.create_task(child())
        await registry.clear()

        # Assert
        self.assertIs(seen_by_child, resource)
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})
