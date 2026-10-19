import os
import unittest

from ddutils.connections import ConnectionManagerFactory, ConnectionProxy, connection_proxy
from ddutils.scoped_registry import ScopedRegistry


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.pool = 'pool'

    async def get(self, key: str) -> str:
        self.calls.append(('get', (key,), {}))
        return f'value:{key}'

    def sync_info(self, *, verbose: bool = False) -> str:
        self.calls.append(('sync_info', (), {'verbose': verbose}))
        return 'info'


class CountingManager:
    """Hands out the registry's client and counts how many times it was borrowed."""

    borrows = 0

    def __init__(self, registry: ScopedRegistry[FakeClient]) -> None:
        self._registry = registry

    async def __aenter__(self) -> FakeClient:
        type(self).borrows += 1
        return await self._registry.set()

    async def __aexit__(self, *exc_info: object) -> None:
        return None


class TestConnectionProxy(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        CountingManager.borrows = 0
        self.clients = {alias: FakeClient() for alias in ('primary', 'replica')}
        registries = {
            alias: ScopedRegistry[FakeClient](create_func=lambda alias=alias: self.clients[alias], scope_func=os.getpid)
            for alias in self.clients
        }
        self.factory = ConnectionManagerFactory(registries, default='primary', connection_manager_class=CountingManager)

    async def test_awaits_async_methods_borrowing_per_call(self):
        # Arrange
        proxy = ConnectionProxy(self.factory)

        # Act
        first = await proxy.get('a')
        second = await proxy.get('b')

        # Assert
        self.assertEqual((first, second), ('value:a', 'value:b'))
        self.assertEqual(self.clients['primary'].calls, [('get', ('a',), {}), ('get', ('b',), {})])
        self.assertEqual(CountingManager.borrows, 2)

    async def test_sync_methods_are_called_inside_the_borrow(self):
        # Arrange
        proxy = ConnectionProxy(self.factory)

        # Act
        result = await proxy.sync_info(verbose=True)

        # Assert
        self.assertEqual(result, 'info')
        self.assertEqual(self.clients['primary'].calls, [('sync_info', (), {'verbose': True})])

    async def test_alias_picks_the_connection(self):
        # Act
        await ConnectionProxy(self.factory, alias='replica').get('a')

        # Assert
        self.assertEqual(self.clients['primary'].calls, [])
        self.assertEqual(self.clients['replica'].calls, [('get', ('a',), {})])

    def test_attributes_are_not_proxied(self):
        # Arrange
        proxy = ConnectionProxy(self.factory)

        # Act & Assert
        self.assertTrue(callable(proxy.pool))  # a method to await, not the client's attribute
        with self.assertRaises(AttributeError):
            proxy._pool  # noqa: B018

    async def test_connection_proxy_helper(self):
        # Act
        client = connection_proxy(self.factory, alias='replica')

        # Assert
        self.assertIsInstance(client, ConnectionProxy)
        self.assertEqual(await client.get('a'), 'value:a')
