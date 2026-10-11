from typing import ClassVar
from unittest import TestCase

from ddutils.class_helpers import require_class_attribute


class Config:
    pass


class BaseConsumer:
    topic: ClassVar[str]
    servers: ClassVar[list[str]]
    batch_size: ClassVar[int] = 100
    config: ClassVar[Config] = Config()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        require_class_attribute(cls, 'topic', str)
        require_class_attribute(cls, 'servers', list)
        require_class_attribute(cls, 'batch_size', int)
        require_class_attribute(cls, 'config', Config)


class TestRequireClassAttribute(TestCase):
    def test_returns_the_value(self):
        # Arrange
        class EventConsumer(BaseConsumer):
            topic = 'events'
            servers = ['kafka:9092']

        # Act & Assert
        self.assertEqual(require_class_attribute(EventConsumer, 'topic', str), 'events')
        self.assertEqual(require_class_attribute(EventConsumer, 'batch_size'), 100)

    def test_missing_attribute(self):
        # Act & Assert
        with self.assertRaisesRegex(AttributeError, '`topic` class attribute of Broken must be set'):

            class Broken(BaseConsumer):
                servers = ['kafka:9092']

    def test_none_counts_as_missing(self):
        # Act & Assert
        with self.assertRaisesRegex(AttributeError, '`config` class attribute of Broken must be set'):

            class Broken(BaseConsumer):
                topic = 'events'
                servers = ['kafka:9092']
                config = None  # type: ignore[assignment]

    def test_empty_values_are_rejected_unless_allowed(self):
        # Act & Assert
        for empty in ('', [], {}, ()):
            with self.subTest(empty=empty), self.assertRaisesRegex(AttributeError, 'must not be empty'):

                class Broken(BaseConsumer):
                    topic = 'events'
                    servers = empty  # type: ignore[assignment]

        class Holder:
            tags = []

        self.assertEqual(require_class_attribute(Holder, 'tags', list, allow_empty=True), [])

    def test_zero_is_a_value(self):
        # Act
        class Impatient(BaseConsumer):
            topic = 'events'
            servers = ['kafka:9092']
            batch_size = 0

        # Assert
        self.assertEqual(Impatient.batch_size, 0)

    def test_wrong_type(self):
        # Act & Assert
        with self.assertRaisesRegex(TypeError, '`servers` class attribute of Broken must be list, got str'):

            class Broken(BaseConsumer):
                topic = 'events'
                servers = 'kafka:9092'  # type: ignore[assignment]

    def test_several_accepted_types_are_named(self):
        # Arrange
        class Holder:
            timeout = '10'

        # Act & Assert
        with self.assertRaisesRegex(TypeError, 'must be int | float, got str'):
            require_class_attribute(Holder, 'timeout', (int, float))

    def test_no_type_check_when_type_is_omitted(self):
        # Arrange
        class Holder:
            anything = object()

        # Act & Assert
        self.assertIs(require_class_attribute(Holder, 'anything'), Holder.anything)
