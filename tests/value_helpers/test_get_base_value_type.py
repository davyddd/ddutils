from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum, IntEnum
from types import NoneType
from unittest import TestCase
from uuid import UUID, uuid4

from parameterized import parameterized

from ddutils.value_helpers import get_base_value_type


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
    RATIO = 0.5
    NOTHING = None
    ID = uuid4()
    AT = datetime(2026, 1, 1, tzinfo=UTC)
    PAIR = (1, 2)


class TestGetBaseValueType(TestCase):
    @parameterized.expand(
        (
            (None, NoneType),
            (True, bool),
            (False, bool),
            (1, int),
            (1.5, float),
            ('x', str),
            (b'x', bytes),
            (bytearray(b'x'), bytearray),
            (datetime(2026, 1, 1), datetime),
            (date(2026, 1, 1), date),
            (time(1, 2), time),
            (timedelta(seconds=1), timedelta),
            (uuid4(), UUID),
            (Decimal('1.1'), Decimal),
        )
    )
    def test_base_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_base_value_type(value), expected_type)

    @parameterized.expand(
        (
            (StrSubclass('x'), str),
            (IntSubclass(2), int),
            (UUIDSubclass(str(uuid4())), UUID),
            (DatetimeSubclass(2026, 1, 1), datetime),
            (DateSubclass(2026, 1, 1), date),
            (DecimalSubclass('1.1'), Decimal),
            (BytearraySubclass(b'x'), bytearray),
        )
    )
    def test_subclass_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_base_value_type(value), expected_type)

    @parameterized.expand(
        (
            (StrMixinEnum.A, str),
            (IntEnumKind.ONE, int),
            (PlainEnum.RED, int),
            (PlainEnum.NAME, str),
            (PlainEnum.RATIO, float),
            (PlainEnum.NOTHING, NoneType),
            (PlainEnum.ID, UUID),
            (PlainEnum.AT, datetime),
        )
    )
    def test_enum_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_base_value_type(value), expected_type)

    @parameterized.expand(
        (
            (object(),),
            ([1],),
            ({'a': 1},),
            (PlainEnum.PAIR,),
        )
    )
    def test_value_without_base_type(self, value):
        # Act & Assert
        with self.assertRaises(TypeError):
            get_base_value_type(value)
