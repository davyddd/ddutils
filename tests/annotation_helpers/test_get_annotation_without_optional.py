from operator import itemgetter
from typing import Union
from unittest import TestCase

from parameterized import parameterized

from ddutils.annotation_helpers import get_annotation_without_optional
from tests.annotation_helpers.constants import (
    COMMON_PYTHON_TYPES,
    GENERIC_DICT_ANNOTATIONS,
    GENERIC_LIST_ANNOTATIONS,
    OPTIONAL_INT_ANNOTATIONS,
)

FLAT_GENERIC_LIST_ANNOTATIONS = list(map(itemgetter(0), GENERIC_LIST_ANNOTATIONS))
FLAT_GENERIC_DICT_ANNOTATIONS = list(map(itemgetter(0), GENERIC_DICT_ANNOTATIONS))


class TestGetAnnotationWithoutOptional(TestCase):
    @parameterized.expand(OPTIONAL_INT_ANNOTATIONS)
    def test_optional_int_annotation(self, annotation):
        # Act & Assert
        self.assertEqual(get_annotation_without_optional(annotation), int)

    @parameterized.expand(
        tuple(
            zip(tuple(Union[annotation, None] for annotation in FLAT_GENERIC_LIST_ANNOTATIONS), FLAT_GENERIC_LIST_ANNOTATIONS)
        )
    )
    def test_optional_generic_list_annotation(self, annotation, expected_annotation):
        # Act & Assert
        self.assertEqual(get_annotation_without_optional(annotation), expected_annotation)

    @parameterized.expand(
        tuple(
            zip(tuple(Union[annotation, None] for annotation in FLAT_GENERIC_DICT_ANNOTATIONS), FLAT_GENERIC_DICT_ANNOTATIONS)
        )
    )
    def test_optional_generic_dict_annotation(self, annotation, expected_annotation):
        # Act & Assert
        self.assertEqual(get_annotation_without_optional(annotation), expected_annotation)

    @parameterized.expand((*COMMON_PYTHON_TYPES, *GENERIC_LIST_ANNOTATIONS, *GENERIC_DICT_ANNOTATIONS))
    def test_non_optional_annotation(self, annotation):
        # Act & Assert
        self.assertEqual(get_annotation_without_optional(annotation), annotation)

    def test_union_without_none(self):
        # Act & Assert
        with self.assertRaises(TypeError):
            get_annotation_without_optional(Union[int, str])
