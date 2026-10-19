from unittest import TestCase
from unittest.mock import patch

from ddutils.safe_decorators import NOT_SET, safe_call


class TestSafeCallDecorator(TestCase):
    def test_success(self):
        # Arrange
        @safe_call()
        def func(a: int, b: int) -> int:
            return a + b

        # Act & Assert
        self.assertEqual(func(2, 3), 5)

    @patch('ddutils.safe_decorators.logger')
    def test_no_default_raises_the_error_unlogged(self, mock_logger):
        # Arrange
        @safe_call()
        def func() -> int:
            raise ValueError('boom')

        # Act & Assert
        with self.assertRaises(ValueError):
            func()
        mock_logger.exception.assert_not_called()

    @patch('ddutils.safe_decorators.logger')
    def test_default_replaces_the_error_and_logs_it(self, mock_logger):
        # Arrange
        @safe_call(default_result='default')
        def func() -> str:
            raise ValueError('boom')

        # Act & Assert
        self.assertEqual(func(), 'default')
        mock_logger.exception.assert_called_once()

    def test_none_is_a_default_too(self):
        # Arrange
        @safe_call(default_result=None, capture_exception=False)
        def func() -> int:
            raise ValueError('boom')

        # Act & Assert
        self.assertIsNone(func())

    @patch('ddutils.safe_decorators.logger')
    def test_retries_then_succeeds(self, mock_logger):
        # Arrange
        calls: list[int] = []
        succeeds_on_attempt = 3

        @safe_call(retries=2)
        def func() -> str:
            calls.append(1)
            if len(calls) < succeeds_on_attempt:
                raise ValueError('boom')
            return 'ok'

        # Act & Assert
        self.assertEqual(func(), 'ok')
        self.assertEqual(len(calls), succeeds_on_attempt)
        self.assertEqual(mock_logger.exception.call_count, 2)

    @patch('ddutils.safe_decorators.logger')
    def test_retries_exhausted_without_default_raises_the_last_error(self, mock_logger):
        # Arrange
        calls: list[int] = []

        @safe_call(retries=1)
        def func() -> str:
            calls.append(1)
            raise ValueError(f'boom {len(calls)}')

        # Act & Assert
        with self.assertRaises(ValueError) as ctx:
            func()
        self.assertEqual(str(ctx.exception), 'boom 2')
        self.assertEqual(len(calls), 2)
        mock_logger.exception.assert_called_once()  # the retried failure; the propagated one is the caller's

    @patch('ddutils.safe_decorators.logger')
    def test_retries_exhausted_with_default_returns_it(self, mock_logger):
        # Arrange
        calls: list[int] = []

        @safe_call(retries=1, default_result=0)
        def func() -> int:
            calls.append(1)
            raise ValueError('boom')

        # Act & Assert
        self.assertEqual(func(), 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(mock_logger.exception.call_count, 2)

    @patch('ddutils.safe_decorators.logger')
    def test_capture_exception_false_does_not_log(self, mock_logger):
        # Arrange
        @safe_call(default_result=None, capture_exception=False)
        def func() -> int:
            raise ValueError('boom')

        # Act & Assert
        self.assertIsNone(func())
        mock_logger.exception.assert_not_called()

    def test_other_exceptions_propagate(self):
        # Arrange
        @safe_call(default_result=None, retries=1, exceptions=(ValueError,))
        def func() -> int:
            raise TypeError('not handled')

        # Act & Assert
        with self.assertRaises(TypeError):
            func()

    def test_negative_retries_rejected(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            safe_call(retries=-1)

    def test_keeps_the_wrapped_name(self):
        # Arrange
        @safe_call()
        def read() -> int:
            return 1

        # Act & Assert
        self.assertEqual(read.__name__, 'read')

    def test_not_set_repr(self):
        self.assertEqual(repr(NOT_SET), 'NOT_SET')
