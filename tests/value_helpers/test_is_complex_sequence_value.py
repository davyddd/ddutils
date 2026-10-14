from collections import deque
from enum import Enum
from unittest import TestCase

from parameterized import parameterized

from ddutils.value_helpers import is_complex_sequence_value


class StrSubclass(str):
    pass


class StrMixinEnum(str, Enum):  # noqa: UP042 - the mixin, not `enum.StrEnum`, is what is under test
    A = 'a'


class TupleSubclass(tuple):
    pass


class TestIsComplexSequenceValue(TestCase):
    @parameterized.expand(
        (
            ([1, 2],),
            ((1, 2),),
            ([],),
            (range(3),),
            (TupleSubclass((1, 2)),),
            (deque((1, 2)),),
        )
    )
    def test_complex_sequence(self, value):
        # Act & Assert
        self.assertTrue(is_complex_sequence_value(value))

    @parameterized.expand(
        (
            ('abc',),
            (b'abc',),
            (bytearray(b'abc'),),
            (StrSubclass('abc'),),
            (StrMixinEnum.A,),
        )
    )
    def test_non_complex_sequence(self, value):
        # Act & Assert
        self.assertFalse(is_complex_sequence_value(value))

    @parameterized.expand(
        (
            ({1, 2},),
            (frozenset((1, 2)),),
            ({'a': 1},),
            (iter([1, 2]),),
            (1,),
            (None,),
        )
    )
    def test_not_a_sequence(self, value):
        # Act & Assert
        self.assertFalse(is_complex_sequence_value(value))
