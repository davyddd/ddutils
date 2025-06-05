import asyncio
import unittest
from copy import deepcopy

from parameterized import parameterized

from ddutils.scoped_registry import ScopedRegistry

DATA = {1: 1}


def scope_func():
    return 1


def sync_create_func():
    return deepcopy(DATA)


async def async_create_func():
    return deepcopy(DATA)


class TestScopedRegistry(unittest.TestCase):
    @parameterized.expand((sync_create_func, async_create_func))
    def test_init(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=scope_func, destructor_method_name='clear')

        # Act & Assert
        self.assertEqual(registry.create_func, func)
        self.assertEqual(registry.scope_func, scope_func)
        self.assertEqual(registry.registry, {})
        self.assertEqual(registry.destructor_method_name, 'clear')
        self.assertIsNone(registry.get())

    @parameterized.expand((sync_create_func, async_create_func))
    def test_call(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=scope_func, destructor_method_name='clear')

        # Act
        result = asyncio.run(registry())

        # Assert
        self.assertEqual(result, DATA)
        self.assertEqual(registry.get(), DATA)

    @parameterized.expand((sync_create_func, async_create_func))
    def test_clear_with_destructor(self, func):
        # Arrange
        registry = ScopedRegistry(create_func=func, scope_func=scope_func, destructor_method_name='clear')

        # Act
        result = asyncio.run(registry())

        # Assert
        self.assertEqual(result, DATA)

        asyncio.run(registry.clear())
        self.assertEqual(result, {})
        self.assertIsNone(registry.get())
