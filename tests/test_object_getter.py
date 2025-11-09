from unittest import TestCase

from ddutils.object_getter import get_object_by_path


class TestObjectGetter(TestCase):
    def test_get_builtin_object(self):
        # Act & Assert
        self.assertEqual(get_object_by_path('builtins.dict'), dict)
        self.assertEqual(get_object_by_path('builtins.list'), list)
        self.assertEqual(get_object_by_path('builtins.str'), str)

    def test_invalid_path_none(self):
        # Act & Assert
        self.assertIsNone(get_object_by_path(None))

    def test_invalid_path_empty_string(self):
        # Act & Assert
        self.assertIsNone(get_object_by_path(''))

    def test_invalid_module(self):
        # Act & Assert
        self.assertIsNone(get_object_by_path('non_existent_module.SomeClass'))

    def test_non_string_path(self):
        # Act & Assert
        self.assertIsNone(get_object_by_path(123))
        self.assertIsNone(get_object_by_path([]))
        self.assertIsNone(get_object_by_path({}))
