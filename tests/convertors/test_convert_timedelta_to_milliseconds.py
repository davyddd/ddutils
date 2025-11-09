from datetime import timedelta
from unittest import TestCase

from parameterized import parameterized

from ddutils.convertors import convert_timedelta_to_milliseconds


class TestConvertTimedeltaToMilliseconds(TestCase):
    @parameterized.expand(
        (
            (timedelta(seconds=0), 0),
            (timedelta(seconds=1), 1000),
            (timedelta(seconds=1.5), 1500),
            (timedelta(milliseconds=500), 500),
            (timedelta(minutes=2), 120000),
            (timedelta(hours=1), 3600000),
            (timedelta(days=1), 86400000),
        )
    )
    def test_convert_zero_timedelta(self, delta, ms):
        # Act
        result = convert_timedelta_to_milliseconds(delta)

        # Assert
        self.assertEqual(result, ms)
