import sys
from datetime import datetime

if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone

    UTC = timezone.utc


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
