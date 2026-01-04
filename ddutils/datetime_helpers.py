import sys
from datetime import datetime

if sys.version_info >= (3, 10):
    from datetime import UTC
else:
    from datetime.timezone import utc as UTC  # noqa: N812


def utc_now() -> datetime:
    return datetime.now(tz=UTC)
