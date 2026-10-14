from typing import Any
from unittest import IsolatedAsyncioTestCase

from ddutils.connections import ConnectionManager, ConnectionManagerFactory
from ddutils.scoped_registry import ScopedRegistry


class FakeClient:
    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True


class CountingManager:
    """A project connection manager: counts enters and exits around the registry's connection."""

    entered = 0
    exited = 0

    def __init__(self, registry: ScopedRegistry[FakeClient]) -> None:
        self._registry = registry

    async def __aenter__(self) -> FakeClient:
        CountingManager.entered += 1
        return await self._registry.set()

    async def __aexit__(self, *exc_info: Any) -> None:
        CountingManager.exited += 1


def process_scope() -> str:
    return 'process'


class TestConnectionManager(IsolatedAsyncioTestCase):
    async def test_connection_is_kept_between_managers(self):
        # Arrange
        registry = ScopedRegistry(create_func=FakeClient, scope_func=process_scope, destructor_method_name='close')

        # Act
        async with ConnectionManager(registry) as first:
            pass
        async with ConnectionManager(registry) as second:
            pass

        # Assert
        self.assertIs(first, second)
        self.assertFalse(first.closed)
        self.assertIs(registry.get(), first)


class TestConnectionManagerFactory(IsolatedAsyncioTestCase):
    def setUp(self):
        self.registries = {
            'primary': ScopedRegistry(create_func=FakeClient, scope_func=process_scope),
            'replica': ScopedRegistry(create_func=FakeClient, scope_func=process_scope),
        }

    async def test_default_connection_manager(self):
        # Arrange
        connect = ConnectionManagerFactory(self.registries, default='primary')

        # Act
        async with connect() as primary:
            pass
        async with connect(alias='replica') as replica:
            pass

        # Assert
        self.assertIsNot(primary, replica)
        self.assertIs(self.registries['primary'].get(), primary)
        self.assertIs(self.registries['replica'].get(), replica)

    async def test_custom_connection_manager(self):
        # Arrange
        connect = ConnectionManagerFactory(self.registries, default='primary', connection_manager_class=CountingManager)

        # Act
        async with connect() as connection:
            pass

        # Assert
        self.assertIs(connection, self.registries['primary'].get())
        self.assertEqual((CountingManager.entered, CountingManager.exited), (1, 1))

    def test_registry_lookup(self):
        # Arrange
        connect = ConnectionManagerFactory(self.registries, default='primary')

        # Act & Assert
        self.assertIs(connect.registry(), self.registries['primary'])
        self.assertIs(connect.registry('replica'), self.registries['replica'])
        with self.assertRaises(KeyError):
            connect.registry('unknown')

    def test_unknown_default(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            ConnectionManagerFactory(self.registries, default='unknown')

    async def test_close_clears_every_registry_of_the_current_scope(self):
        # Arrange
        registries = {
            'primary': ScopedRegistry(create_func=FakeClient, scope_func=process_scope, destructor_method_name='close'),
            'replica': ScopedRegistry(create_func=FakeClient, scope_func=process_scope, destructor_method_name='close'),
            'unused': ScopedRegistry(create_func=FakeClient, scope_func=process_scope, destructor_method_name='close'),
        }
        factory = ConnectionManagerFactory(registries, default='primary')
        async with factory() as primary, factory(alias='replica') as replica:
            pass

        # Act
        await factory.close()
        await factory.close()  # nothing left, no error

        # Assert
        self.assertTrue(primary.closed)
        self.assertTrue(replica.closed)
        self.assertIsNone(registries['primary'].get())
        self.assertIsNone(registries['unused'].get())
