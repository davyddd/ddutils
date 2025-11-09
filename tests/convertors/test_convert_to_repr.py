from dataclasses import dataclass
from unittest import TestCase

from ddutils.convertors import convert_to_repr


class User:  # noqa: B903
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age


@dataclass
class Person:
    name: str
    age: int
    city: str
    active: bool


class EmptyClass:
    pass


class ClassWithPrivateAttrs:
    def __init__(self, public: str, private: str):
        self.public = public
        self._private = private
        self.__very_private = 'secret'


class MixedTypes:
    def __init__(self):
        self.string = 'test'
        self.number = 42
        self.float_val = 3.14
        self.bool_val = False
        self.none_val = None
        self.list_val = [1, 2, 3]


class TestConvertToRepr(TestCase):
    def test_convert_simple_object_to_repr(self):
        # Arrange
        obj = User('John', 30)

        # Act
        result = convert_to_repr(obj)

        # Assert
        self.assertEqual(result, "User(name='John', age=30)")

    def test_convert_object_with_multiple_attributes(self):
        # Arrange
        obj = Person('Alice', 25, 'NYC', True)

        # Act
        result = convert_to_repr(obj)

        # Assert
        self.assertEqual(result, "Person(name='Alice', age=25, city='NYC', active=True)")

    def test_convert_object_with_no_attributes(self):
        # Arrange
        obj = EmptyClass()

        # Act
        result = convert_to_repr(obj)

        # Assert
        self.assertEqual(result, 'EmptyClass()')

    def test_convert_object_excludes_private_attributes(self):
        # Arrange
        obj = ClassWithPrivateAttrs('visible', 'hidden')

        # Act
        result = convert_to_repr(obj)

        # Assert
        self.assertEqual(result, "ClassWithPrivateAttrs(public='visible')")

    def test_convert_object_with_various_types(self):
        # Arrange
        obj = MixedTypes()

        # Act
        result = convert_to_repr(obj)

        # Assert
        self.assertEqual(
            result, "MixedTypes(string='test', number=42, float_val=3.14, bool_val=False, none_val=None, list_val=[1, 2, 3])"
        )
