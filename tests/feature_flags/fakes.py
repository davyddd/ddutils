from ddutils.feature_flags import FeatureFlagRecord, FeatureFlagStorage, FeatureFlagStorageError


class MemoryFeatureFlagStorage(FeatureFlagStorage):
    """The reference storage for the tests: a dict, with a switch that makes every call fail."""

    def __init__(self, records: dict[str, FeatureFlagRecord] | None = None) -> None:
        self.records = dict(records or {})
        self.failing = False
        self.reads = 0

    def _check(self) -> None:
        if self.failing:
            raise FeatureFlagStorageError() from ConnectionError('storage is down')

    async def get(self, name: str) -> FeatureFlagRecord | None:
        self._check()
        self.reads += 1
        return self.records.get(name)

    async def get_map(self) -> dict[str, FeatureFlagRecord]:
        self._check()
        return dict(self.records)

    async def put(self, name: str, record: FeatureFlagRecord) -> None:
        self._check()
        self.records[name] = record

    async def delete(self, name: str) -> bool:
        self._check()
        return self.records.pop(name, None) is not None
