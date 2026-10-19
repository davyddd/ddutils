from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from ddutils.safe_decorators import safe_call


class TestSafeCallAsyncDecorator(IsolatedAsyncioTestCase):
    async def test_success(self):
        # Arrange
        @safe_call()
        async def func(a: int, b: int) -> int:
            return a + b

        # Act & Assert
        self.assertEqual(await func(2, 3), 5)

    @patch('ddutils.safe_decorators.logger')
    async def test_no_default_raises_the_error_unlogged(self, mock_logger):
        # Arrange
        @safe_call()
        async def func() -> int:
            raise ValueError('boom')

        # Act & Assert
        with self.assertRaises(ValueError):
            await func()
        mock_logger.exception.assert_not_called()

    @patch('ddutils.safe_decorators.logger')
    async def test_default_replaces_the_error_and_logs_it(self, mock_logger):
        # Arrange
        @safe_call(default_result='default')
        async def func() -> str:
            raise ValueError('boom')

        # Act & Assert
        self.assertEqual(await func(), 'default')
        mock_logger.exception.assert_called_once()

    @patch('ddutils.safe_decorators.logger')
    async def test_retries_then_succeeds(self, mock_logger):
        # Arrange
        calls: list[int] = []
        succeeds_on_attempt = 3

        @safe_call(retries=2)
        async def func() -> str:
            calls.append(1)
            if len(calls) < succeeds_on_attempt:
                raise ValueError('boom')
            return 'ok'

        # Act & Assert
        self.assertEqual(await func(), 'ok')
        self.assertEqual(len(calls), succeeds_on_attempt)
        self.assertEqual(mock_logger.exception.call_count, 2)

    @patch('ddutils.safe_decorators.logger')
    async def test_retries_exhausted_without_default_raises_the_last_error(self, mock_logger):
        # Arrange
        calls: list[int] = []

        @safe_call(retries=1)
        async def func() -> str:
            calls.append(1)
            raise ValueError(f'boom {len(calls)}')

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            await func()
        self.assertEqual(str(ctx.exception), 'boom 2')
        mock_logger.exception.assert_called_once()

    async def test_retries_exhausted_with_default_returns_it(self):
        # Arrange
        calls: list[int] = []

        @safe_call(retries=1, default_result=0, capture_exception=False)
        async def func() -> int:
            calls.append(1)
            raise ValueError('boom')

        # Act & Assert
        self.assertEqual(await func(), 0)
        self.assertEqual(len(calls), 2)

    async def test_other_exceptions_propagate(self):
        # Arrange
        @safe_call(default_result=None, exceptions=(ValueError,))
        async def func() -> int:
            raise TypeError('not handled')

        # Act & Assert
        with self.assertRaises(TypeError):
            await func()

    async def test_keeps_the_wrapped_name(self):
        # Arrange
        @safe_call()
        async def read() -> int:
            return 1

        # Act & Assert
        self.assertEqual(read.__name__, 'read')
