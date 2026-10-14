from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, IntEnum
from unittest import TestCase
from uuid import UUID, uuid4

from parameterized import parameterized

from ddutils.convertors import BASE_VALUE_CONVERTORS, convert_to_base_value
from ddutils.value_helpers import BASE_VALUE_TYPES


class StrSubclass(str):
    pass


class IntSubclass(int):
    pass


class UUIDSubclass(UUID):
    pass


class DatetimeSubclass(datetime):
    pass


class DateSubclass(date):
    pass


class TimeSubclass(time):
    pass


class TimedeltaSubclass(timedelta):
    pass


class DecimalSubclass(Decimal):
    pass


class BytearraySubclass(bytearray):
    pass


class StrMixinEnum(str, Enum):  # noqa: UP042 - the mixin, not `enum.StrEnum`, is what is under test
    A = 'a'


class IntEnumKind(IntEnum):
    ONE = 1


class PlainEnum(Enum):
    RED = 1
    NAME = 'red'
    ID = UUID('12345678-1234-5678-1234-567812345678')


UUID_VALUE = uuid4()
DATETIME_VALUE = datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC, fold=1)


class TestConvertToBaseValue(TestCase):
    @parameterized.expand(
        (
            (None, None),
            (True, True),
            (1, 1),
            (1.5, 1.5),
            ('x', 'x'),
            (b'x', b'x'),
            (StrSubclass('x'), 'x'),
            (IntSubclass(2), 2),
            (UUIDSubclass(str(UUID_VALUE)), UUID_VALUE),
            (DatetimeSubclass(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC, fold=1), DATETIME_VALUE),
            (DateSubclass(2026, 1, 2), date(2026, 1, 2)),
            (TimeSubclass(3, 4, 5, 6, tzinfo=UTC, fold=1), time(3, 4, 5, 6, tzinfo=UTC, fold=1)),
            (TimedeltaSubclass(days=1, seconds=2, microseconds=3), timedelta(days=1, seconds=2, microseconds=3)),
            (DecimalSubclass('1.10'), Decimal('1.10')),
            (BytearraySubclass(b'x'), bytearray(b'x')),
            (StrMixinEnum.A, 'a'),
            (IntEnumKind.ONE, 1),
            (PlainEnum.RED, 1),
            (PlainEnum.NAME, 'red'),
            (PlainEnum.ID, UUID('12345678-1234-5678-1234-567812345678')),
        )
    )
    def test_convert(self, value, expected):
        # Act
        result = convert_to_base_value(value)

        # Assert
        self.assertEqual(result, expected)
        self.assertIs(type(result), type(expected))

    def test_str_enum_is_not_stringified_by_name(self):
        # `str(StrMixinEnum.A)` is 'StrMixinEnum.A'; the member must be converted through its value
        self.assertEqual(convert_to_base_value(StrMixinEnum.A), 'a')

    def test_datetime_keeps_tzinfo_and_fold(self):
        # Act
        result = convert_to_base_value(DatetimeSubclass(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC, fold=1))

        # Assert
        self.assertIs(result.tzinfo, UTC)
        self.assertEqual(result.fold, 1)

    def test_datetime_subclass_does_not_become_date(self):
        # Act & Assert
        self.assertIs(type(convert_to_base_value(DatetimeSubclass(2026, 1, 2))), datetime)

    def test_timedelta_keeps_microseconds_on_large_values(self):
        # Arrange
        value = TimedeltaSubclass(days=10**6, seconds=1, microseconds=1)

        # Act & Assert
        self.assertEqual(convert_to_base_value(value), timedelta(days=10**6, seconds=1, microseconds=1))

    @parameterized.expand(((object(),), ([1],), ({'a': 1},)))
    def test_value_without_base_type(self, value):
        # Act & Assert
        with self.assertRaises(TypeError):
            convert_to_base_value(value)

    def test_every_base_value_type_has_a_convertor(self):
        # Act & Assert
        self.assertEqual(set(BASE_VALUE_CONVERTORS), set(BASE_VALUE_TYPES))
