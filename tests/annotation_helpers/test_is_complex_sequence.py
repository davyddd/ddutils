from enum import Enum
from unittest import TestCase

from parameterized import parameterized

from ddutils.annotation_helpers import NON_COMPLEX_SEQUENCE_TYPES, is_complex_sequence
from tests.annotation_helpers.constants import GENERIC_DICT_ANNOTATIONS, GENERIC_LIST_ANNOTATIONS


class StrSubclass(str):
    pass


class BytesSubclass(bytes):
    pass


class StrMixinEnum(str, Enum):  # noqa: UP042 - the mixin, not `enum.StrEnum`, is what is under test
    A = 'a'


class TupleSubclass(tuple):
    pass


class TestIsComplexSequence(TestCase):
    @parameterized.expand(GENERIC_LIST_ANNOTATIONS)
    def test_generic_list_annotation(self, annotation):
        # Act & Assert
        self.assertTrue(is_complex_sequence(annotation))

    @parameterized.expand(GENERIC_DICT_ANNOTATIONS)
    def test_generic_dict_annotation(self, annotation):
        # Act & Assert
        self.assertFalse(is_complex_sequence(annotation))

    @parameterized.expand(NON_COMPLEX_SEQUENCE_TYPES)
    def test_non_complex_sequence(self, annotation):
        # Act & Assert
        self.assertFalse(is_complex_sequence(annotation))

    @parameterized.expand(((StrSubclass,), (BytesSubclass,), (StrMixinEnum,)))
    def test_non_complex_sequence_subclass(self, annotation):
        # Act & Assert
        self.assertFalse(is_complex_sequence(annotation))

    def test_complex_sequence_subclass(self):
        # Act & Assert
        self.assertTrue(is_complex_sequence(TupleSubclass))
