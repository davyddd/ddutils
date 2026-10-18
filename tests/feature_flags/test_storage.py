from unittest import IsolatedAsyncioTestCase

from ddutils.feature_flags import FeatureFlagRecord
from tests.feature_flags.fakes import MemoryFeatureFlagStorage


class TestFeatureFlagStorage(IsolatedAsyncioTestCase):
    async def test_rename_default_is_put_then_delete(self):
        # Arrange
        storage = MemoryFeatureFlagStorage({'old': FeatureFlagRecord(enabled=True)})

        # Act
        await storage.rename('old', 'new', FeatureFlagRecord(enabled=True, proportion=1.0))

        # Assert
        self.assertEqual(storage.records, {'new': FeatureFlagRecord(enabled=True, proportion=1.0)})
