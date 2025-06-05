import unittest

from ddutils.class_helpers import classproperty


class TestClass:
    _value = 'test_value'

    @classproperty
    def value(cls) -> str:
        """This is a test docstring"""
        return cls._value


class TestClassProperty(unittest.TestCase):
    def test_basic_functionality(self):
        # Act & Assert
        self.assertEqual(TestClass.value, 'test_value')

    def test_access_through_instance(self):
        # Act & Assert
        self.assertEqual(TestClass().value, 'test_value')

    def test_docstring_preservation(self):
        # Act & Assert
        self.assertEqual(TestClass.__dict__['value'].__doc__, 'This is a test docstring')

    def test_name_preservation(self):
        # Act & Assert
        self.assertEqual(TestClass.__dict__['value'].__name__, 'value')
