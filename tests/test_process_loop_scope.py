import asyncio
import os
import unittest

from ddutils.scoped_registry import ScopedRegistry, process_loop_scope


class TestProcessLoopScope(unittest.IsolatedAsyncioTestCase):
    async def test_key_is_pid_and_running_loop(self):
        self.assertEqual(process_loop_scope(), (os.getpid(), asyncio.get_running_loop()))

    def test_requires_a_running_loop(self):
        with self.assertRaises(RuntimeError):
            process_loop_scope()

    def test_each_loop_gets_its_own_value(self):
        # Arrange
        created: list[object] = []

        def create():
            value = object()
            created.append(value)
            return value

        registry = ScopedRegistry(create_func=create, scope_func=process_loop_scope)

        # Act
        first = asyncio.run(registry.set())
        second = asyncio.run(registry.set())

        # Assert
        self.assertIsNot(first, second)
        self.assertEqual(len(created), 2)
