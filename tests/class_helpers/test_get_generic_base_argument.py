from typing import Generic, TypeVar
from unittest import TestCase

from ddutils.class_helpers import get_generic_base_argument

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class Repository(Generic[T]):
    pass


class Mapping(Generic[K, V]):
    pass


class User:
    pass


class TestGetGenericBaseArgument(TestCase):
    def test_bound_argument(self):
        # Arrange
        class UserRepository(Repository[User]):
            pass

        # Act & Assert
        self.assertIs(get_generic_base_argument(UserRepository, Repository), User)

    def test_argument_by_position(self):
        # Arrange
        class UserMapping(Mapping[str, User]):
            pass

        # Act & Assert
        self.assertIs(get_generic_base_argument(UserMapping, Mapping), str)
        self.assertIs(get_generic_base_argument(UserMapping, Mapping, position=1), User)
        self.assertIsNone(get_generic_base_argument(UserMapping, Mapping, position=2))

    def test_unparametrized_subclass(self):
        # Arrange
        class PlainRepository(Repository):  # type: ignore[type-arg]
            pass

        # Act & Assert
        self.assertIsNone(get_generic_base_argument(PlainRepository, Repository))

    def test_still_generic_subclass_returns_the_type_var(self):
        # Arrange
        class BaseRepository(Repository[T]):
            pass

        # Act & Assert
        self.assertIs(get_generic_base_argument(BaseRepository, Repository), T)

    def test_other_bases_are_ignored(self):
        # Arrange
        class Mixin:
            pass

        class UserRepository(Mixin, Repository[User]):
            pass

        # Act & Assert
        self.assertIs(get_generic_base_argument(UserRepository, Repository), User)
        self.assertIsNone(get_generic_base_argument(UserRepository, Mapping))

    def test_class_without_generic_bases(self):
        # Act & Assert
        self.assertIsNone(get_generic_base_argument(User, Repository))
