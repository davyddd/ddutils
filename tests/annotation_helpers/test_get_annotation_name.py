from collections.abc import Callable
from typing import List, Literal, Optional, Union  # noqa: UP035
from unittest import TestCase

from parameterized import parameterized

from ddutils.annotation_helpers import get_annotation_name


class User:
    pass


class TestGetAnnotationName(TestCase):
    @parameterized.expand(
        [
            (int, 'int'),
            (User, 'User'),
            (None, 'None'),
            (type(None), 'None'),
            ((int, float), 'int | float'),
            ((int, User, str), 'int | User | str'),
            (int | None, 'int | None'),
            (Optional[int], 'int | None'),  # noqa: UP045
            (Union[int, str], 'int | str'),  # noqa: UP007
            (list[int], 'list[int]'),
            (List[int], 'list[int]'),  # noqa: UP006
            (dict[str, User | None], 'dict[str, User | None]'),
            (tuple[int, ...], 'tuple[int, ...]'),
            (Literal[0, 1, 'all'], "Literal[0, 1, 'all']"),
            (Callable[[int, str], User], 'Callable[[int, str], User]'),
        ]
    )
    def test_names(self, annotation, expected):
        # Act & Assert
        self.assertEqual(get_annotation_name(annotation), expected)
