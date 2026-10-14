from enum import Enum, IntEnum
from unittest import TestCase

from parameterized import parameterized

from ddutils.convertors import convert_to_builtin


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


class TestConvertToBuiltin(TestCase):
    @parameterized.expand(
        (
            (True, True),
            (1, 1),
            (1.5, 1.5),
            ('x', 'x'),
            (b'x', b'x'),
            (StrSubclass('x'), 'x'),
            (IntSubclass(2), 2),
            (StrMixinEnum.A, 'a'),
            (IntEnumKind.ONE, 1),
            (PlainEnum.RED, 1),
            (PlainEnum.NAME, 'red'),
        )
    )
    def test_convert(self, value, expected):
        # Act
        result = convert_to_builtin(value)

        # Assert
        self.assertEqual(result, expected)
        self.assertIs(type(result), type(expected))

    def test_str_enum_is_not_stringified_by_name(self):
        # `str(StrMixinEnum.A)` is 'StrMixinEnum.A'; the member must be converted through its value
        self.assertEqual(convert_to_builtin(StrMixinEnum.A), 'a')

    @parameterized.expand(((object(),), (None,), ([1],)))
    def test_value_without_builtin_base(self, value):
        # Act & Assert
        with self.assertRaises(TypeError):
            convert_to_builtin(value)
