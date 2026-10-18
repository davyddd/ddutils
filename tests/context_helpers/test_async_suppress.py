from contextlib import asynccontextmanager
from unittest import IsolatedAsyncioTestCase

from ddutils.context_helpers import async_suppress


class TestAsyncSuppress(IsolatedAsyncioTestCase):
    async def test_swallows_the_listed_exceptions(self):
        # Act
        reached = False
        async with async_suppress(KeyError, ValueError):
            raise ValueError('x')
            reached = True  # type: ignore[unreachable]  # noqa: F841

        # Assert: the block was left at the raise
        self.assertFalse(reached)

    async def test_other_exceptions_propagate(self):
        # Act & Assert
        with self.assertRaises(TypeError):
            async with async_suppress(ValueError):
                raise TypeError('x')

    async def test_nothing_raised(self):
        # Act
        async with async_suppress(ValueError):
            value = 1

        # Assert
        self.assertEqual(value, 1)

    async def test_shares_one_async_with_statement(self):
        # Arrange
        events = []

        @asynccontextmanager
        async def resource():
            events.append('enter')
            try:
                yield
            finally:
                events.append('exit')

        # Act
        async with async_suppress(ValueError), resource():
            raise ValueError('x')

        # Assert: the resource was released, the error swallowed
        self.assertEqual(events, ['enter', 'exit'])
