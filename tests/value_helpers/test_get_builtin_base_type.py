from enum import Enum, IntEnum
from unittest import TestCase

from parameterized import parameterized

from ddutils.value_helpers import get_builtin_base_type


class StrSubclass(str):
    pass


class IntSubclass(int):
    pass


class StrMixinEnum(str, Enum):  # noqa: UP042 - the mixin, not `enum.StrEnum`, is what is under test
    A = 'a'


class IntEnumKind(IntEnum):
    ONE = 1


class PlainEnum(Enum):
    RED = 1
    NAME = 'red'
    RATIO = 0.5
    PAIR = (1, 2)


class TestGetBuiltinBaseType(TestCase):
    @parameterized.expand(
        (
            (True, bool),
            (False, bool),
            (1, int),
            (1.5, float),
            ('x', str),
            (b'x', bytes),
        )
    )
    def test_builtin_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_builtin_base_type(value), expected_type)

    @parameterized.expand(
        (
            (StrSubclass('x'), str),
            (IntSubclass(2), int),
        )
    )
    def test_subclass_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_builtin_base_type(value), expected_type)

    @parameterized.expand(
        (
            (StrMixinEnum.A, str),
            (IntEnumKind.ONE, int),
            (PlainEnum.RED, int),
            (PlainEnum.NAME, str),
            (PlainEnum.RATIO, float),
        )
    )
    def test_enum_value(self, value, expected_type):
        # Act & Assert
        self.assertIs(get_builtin_base_type(value), expected_type)

    @parameterized.expand(
        (
            (object(),),
            (None,),
            (bytearray(b'x'),),
            ([1],),
            (PlainEnum.PAIR,),
        )
    )
    def test_value_without_builtin_base(self, value):
        # Act & Assert
        with self.assertRaises(TypeError):
            get_builtin_base_type(value)
