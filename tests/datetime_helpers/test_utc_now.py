import sys
from datetime import datetime
from unittest import TestCase

from ddutils.datetime_helpers import utc_now

if sys.version_info >= (3, 10):
    from datetime import UTC
else:
    from datetime.timezone import utc as UTC  # noqa: N812


class TestUtcNow(TestCase):
    def test_returns_datetime(self):
        # Act
        result = utc_now()

        # Assert
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.tzinfo, UTC)

    def test_returns_current_time(self):
        # Act
        before = datetime.now(tz=UTC)
        result = utc_now()
        after = datetime.now(tz=UTC)

        # Assert
        self.assertGreaterEqual(result, before)
        self.assertLessEqual(result, after)
