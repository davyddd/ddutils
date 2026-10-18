from dataclasses import FrozenInstanceError
from unittest import TestCase

from parameterized import parameterized

from ddutils.feature_flags import DEFAULT_PROPORTION, FeatureFlagRecord


class TestFeatureFlagRecord(TestCase):
    def test_defaults(self):
        # Act & Assert
        self.assertEqual(FeatureFlagRecord(), FeatureFlagRecord(enabled=False, proportion=DEFAULT_PROPORTION, payload={}))

    def test_is_frozen(self):
        # Act & Assert
        with self.assertRaises(FrozenInstanceError):
            FeatureFlagRecord().enabled = True  # type: ignore[misc]

    def test_round_trip(self):
        # Act
        record = FeatureFlagRecord.from_dict({'enabled': True, 'proportion': 0.5, 'payload': {'ttl': 10}})

        # Assert
        self.assertEqual(record, FeatureFlagRecord(enabled=True, proportion=0.5, payload={'ttl': 10}))
        self.assertEqual(record.to_dict(), {'enabled': True, 'proportion': 0.5, 'payload': {'ttl': 10}})

    def test_payload_is_copied(self):
        # Arrange
        payload = {'a': 1}

        # Act
        record = FeatureFlagRecord(payload=payload)
        payload['b'] = 2

        # Assert
        self.assertEqual(record.payload, {'a': 1})

    @parameterized.expand(
        [
            (True, True),
            (1, True),
            ('1', True),
            ('true', True),
            ('True', True),
            ('yes', True),
            (b'on', True),
            (0, False),
            ('0', False),
            ('false', False),
            ('no', False),
        ]
    )
    def test_enabled_takes_what_a_storage_may_hold_for_a_bool(self, raw, expected):
        # Act & Assert
        self.assertEqual(FeatureFlagRecord(enabled=raw).enabled, expected)

    def test_proportion_takes_numbers_and_numeric_strings(self):
        # Act & Assert
        self.assertEqual(FeatureFlagRecord(proportion=1).proportion, 1.0)
        self.assertEqual(FeatureFlagRecord(proportion='0.25').proportion, 0.25)  # type: ignore[arg-type]

    @parameterized.expand(
        [
            ('not a mapping', 'garbage'),
            ('unknown field', {'value': True}),
            ('enabled garbage', {'enabled': 'yes please'}),
            ('enabled 2', {'enabled': 2}),
            ('enabled none', {'enabled': None}),
            ('proportion too high', {'proportion': 3}),
            ('proportion negative', {'proportion': -0.1}),
            ('proportion garbage', {'proportion': 'x'}),
            ('proportion bool', {'proportion': True}),
            ('payload not a mapping', {'payload': [1, 2]}),
        ]
    )
    def test_malformed_data_is_rejected(self, _name, data):
        # Act & Assert
        with self.assertRaises(ValueError):
            FeatureFlagRecord.from_dict(data)
