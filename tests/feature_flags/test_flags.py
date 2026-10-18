from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from ddutils.feature_flags import ERROR_TTL, FeatureFlagRecord, FeatureFlags
from tests.feature_flags.fakes import MemoryFeatureFlagStorage

ON = FeatureFlagRecord(enabled=True, proportion=1.0, payload={'ttl': 10, 'topic': 'events'})
HALF = FeatureFlagRecord(enabled=True, proportion=0.5, payload={'ttl': 10})
OFF_HALF = FeatureFlagRecord(enabled=False, proportion=0.5)
SUBJECTS = 200
EXPECTED_SHARE = (60, 140)  # 0.5 of 200 keys, with room for the hash distribution


class TestFeatureFlags(IsolatedAsyncioTestCase):
    def setUp(self):
        self.storage = MemoryFeatureFlagStorage({'on': ON, 'half': HALF, 'off_half': OFF_HALF})
        self.flags = FeatureFlags(self.storage)

    async def test_is_enabled_and_get_payload(self):
        # Act & Assert: proportion 1.0 is on for everyone; a missing flag is off with an empty payload
        self.assertTrue(await self.flags.is_enabled('on'))
        self.assertTrue(await self.flags.is_enabled('on', 'user-1'))
        self.assertEqual(await self.flags.get_payload('on'), {'ttl': 10, 'topic': 'events'})
        self.assertFalse(await self.flags.is_enabled('missing'))
        self.assertEqual(await self.flags.get_payload('missing'), {})

    async def test_proportion_without_an_idempotent_key_is_random_per_call(self):
        # Act
        with patch('ddutils.feature_flags.random.random', return_value=0.9):
            out = await self.flags.is_enabled('half')
        with patch('ddutils.feature_flags.random.random', return_value=0.1):
            in_ = await self.flags.is_enabled('half')

        # Assert: the payload is as stored either way
        self.assertFalse(out)
        self.assertTrue(in_)
        self.assertEqual(await self.flags.get_payload('half'), {'ttl': 10})

    async def test_proportion_with_an_idempotent_key_is_repeatable(self):
        # Act
        decisions = {key: await self.flags.is_enabled('half', key) for key in range(SUBJECTS)}
        again = {key: await self.flags.is_enabled('half', key) for key in range(SUBJECTS)}

        # Assert: the same key always lands on the same side, and the share is about the proportion
        self.assertEqual(decisions, again)
        self.assertTrue(EXPECTED_SHARE[0] < sum(decisions.values()) < EXPECTED_SHARE[1], sum(decisions.values()))

    async def test_an_off_flag_is_never_enabled(self):
        # Act & Assert
        self.assertFalse(await self.flags.is_enabled('off_half'))
        self.assertFalse(any([await self.flags.is_enabled('off_half', key) for key in range(50)]))

    async def test_record_is_cached_for_the_ttl(self):
        # Act
        await self.flags.is_enabled('on')
        await self.flags.is_enabled('on', 'user-1')
        await self.flags.get_payload('on')

        # Assert: one read, the calls share the cache
        self.assertEqual(self.storage.reads, 1)

        # Act: the entry expired
        with patch('ddutils.feature_flags.time.time', return_value=self.flags._cache['on'].expiration_time + 1):
            await self.flags.is_enabled('on')

        # Assert
        self.assertEqual(self.storage.reads, 2)

    async def test_storage_error_serves_the_last_known_record_with_a_backoff(self):
        # Arrange
        await self.flags.is_enabled('on')
        self.storage.failing = True
        now = self.flags._cache['on'].expiration_time + 1

        # Act: three failed re-reads, each after the previous retry window
        retries = []
        for _ in range(3):
            with patch('ddutils.feature_flags.time.time', return_value=now), self.assertLogs('ddutils.feature_flags', 'ERROR'):
                flag = await self.flags.is_enabled('on')
                unknown = await self.flags.is_enabled('never-seen')
            retries.append(self.flags._cache['on'].expiration_time - now)
            now = self.flags._cache['on'].expiration_time + 1

        # Assert: the last known record for `on`, the defaults for the unknown flag, retries 1s, 2s, 4s
        self.assertTrue(flag)
        self.assertFalse(unknown)
        self.assertEqual(retries, [ERROR_TTL, ERROR_TTL * 2, ERROR_TTL * 4])

    async def test_backoff_is_capped_and_reset_by_a_successful_read(self):
        # Arrange
        flags = FeatureFlags(self.storage, base_ttl=3)
        await flags.is_enabled('on')
        self.storage.failing = True
        now = flags._cache['on'].expiration_time + 1
        retries = []
        for _ in range(4):
            with patch('ddutils.feature_flags.time.time', return_value=now), self.assertLogs('ddutils.feature_flags', 'ERROR'):
                await flags.is_enabled('on')
            retries.append(flags._cache['on'].expiration_time - now)
            now = flags._cache['on'].expiration_time + 1

        # Assert: 1s, 2s, then capped at base_ttl
        self.assertEqual(retries, [1, 2, 3, 3])
        self.assertEqual(flags._cache['on'].failures, 4)

        # Act: the storage is back
        self.storage.failing = False
        with patch('ddutils.feature_flags.time.time', return_value=now):
            await flags.is_enabled('on')

        # Assert
        self.assertEqual(flags._cache['on'].failures, 0)
