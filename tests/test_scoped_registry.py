import asyncio
import unittest

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

    def test_sync_set(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func)

        # Act
        first = registry.sync_set(name='first')
        second = registry.sync_set(name='second')

        # Assert
        self.assertIs(first, second)
        self.assertEqual(first.name, 'first')
        self.assertIs(registry.get(), first)

    def test_sync_set_rejects_async_create_func(self):
        # Arrange
        registry = ScopedRegistry(create_func=async_create_func, scope_func=constant_scope_func)

        # Act & Assert
        with self.assertRaises(TypeError):
            registry.sync_set()
        self.assertEqual(registry.registry, {})

    @parameterized.expand((sync_create_func, async_create_func))
    async def test_async_set(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func)

        # Act
        first = await registry.async_set(name='first')
        second = await registry.async_set(name='second')

        # Assert
        self.assertIs(first, second)
        self.assertEqual(first.name, 'first')
        self.assertIs(registry.get(), first)

    async def test_async_set_race(self):
        # Arrange
        calls = 0

        async def slow_create_func() -> Resource:
            nonlocal calls
            calls += 1
            await asyncio.sleep(0)
            return Resource()

        registry = ScopedRegistry(create_func=slow_create_func, scope_func=constant_scope_func)

        # Act
        results = await asyncio.gather(*(registry.async_set() for _ in range(5)))

        # Assert
        self.assertEqual(calls, 1)
        self.assertEqual(len(registry.registry), 1)
        self.assertTrue(all(result is results[0] for result in results))

    @parameterized.expand((sync_create_func, async_create_func))
    async def test_async_clear_with_destructor(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=constant_scope_func, destructor_method_name='close')
        resource = await registry.async_set()

        # Act
        await registry.async_clear()

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertIsNone(registry.get())
        self.assertEqual(registry.registry, {})

    async def test_async_clear_with_async_destructor(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='aclose')
        resource = await registry.async_set()

        # Act
        await registry.async_clear()

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})

    def test_sync_clear(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')
        resource = registry.sync_set()

        # Act
        registry.sync_clear()

        # Assert
        self.assertEqual(resource.closed, 1)
        self.assertEqual(registry.registry, {})

    def test_sync_clear_rejects_async_destructor(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='aclose')
        registry.sync_set()

        # Act & Assert
        with self.assertRaises(TypeError):
            registry.sync_clear()

    async def test_clear_specific_scopes(self):
        # Arrange
        current = {'key': 'a'}
        registry = ScopedRegistry(
            create_func=sync_create_func, scope_func=lambda: current['key'], destructor_method_name='close'
        )
        resource_a = await registry.async_set(name='a')
        current['key'] = 'b'
        resource_b = await registry.async_set(name='b')

        # Act
        await registry.async_clear('a')

        # Assert
        self.assertEqual(resource_a.closed, 1)
        self.assertEqual(resource_b.closed, 0)
        self.assertEqual(registry.registry, {'b': resource_b})

    async def test_clear_without_entries_does_nothing(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, scope_func=constant_scope_func, destructor_method_name='close')

        # Act & Assert
        await registry.async_clear()
        registry.sync_clear('unknown')
        self.assertEqual(registry.registry, {})

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

    async def test_scope_without_scope_func_is_inherited_by_child_tasks(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, destructor_method_name='close')

        async def child():
            return registry.get()

        # Act
        async with registry.scope() as resource:
            child_result, *_ = await asyncio.gather(child(), child())
            created_task_result = await asyncio.create_task(child())

        # Assert
        self.assertIs(child_result, resource)
        self.assertIs(created_task_result, resource)
        self.assertEqual(resource.closed, 1)
        self.assertIsNone(registry.get())
        self.assertIsNone(registry._key_var.get())

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

    async def test_parallel_scopes_without_scope_func_get_distinct_values(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func, destructor_method_name='close')

        async def work():
            async with registry.scope() as resource:
                await asyncio.sleep(0)
                return resource

        # Act
        first, second = await asyncio.gather(work(), work())

        # Assert
        self.assertIsNot(first, second)
        self.assertEqual((first.closed, second.closed), (1, 1))
        self.assertEqual(registry.registry, {})

    async def test_outside_scope_without_scope_func(self):
        # Arrange
        registry = ScopedRegistry(create_func=sync_create_func)

        # Act & Assert
        self.assertIsNone(registry.get())
        self.assertEqual(registry.registry, {})
        with self.assertRaises(RuntimeError):
            await registry.async_set()
        with self.assertRaises(RuntimeError):
            registry.sync_set()
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
