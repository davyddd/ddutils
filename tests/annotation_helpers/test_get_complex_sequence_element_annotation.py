from unittest import TestCase

from parameterized import parameterized

from ddutils.annotation_helpers import get_complex_sequence_element_annotation
from tests.annotation_helpers.constants import GENERIC_LIST_ANNOTATIONS


class TestGetComplexSequenceElementAnnotation(TestCase):
    @parameterized.expand(GENERIC_LIST_ANNOTATIONS)
    def test_generic_list_annotation(self, annotation):
        # Act & Assert
        self.assertEqual(get_complex_sequence_element_annotation(annotation), int)
