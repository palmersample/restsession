"""
Test cases for the metaclass used to define the RestSessionSingleton class.
"""
import logging
import pytest
from restsession.metaclass import Singleton  # pylint: disable=import-error

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.code, pytest.mark.exceptions,]


class DummySingleton(metaclass=Singleton):  # pylint: disable=too-few-public-methods
    """
    Fixture for a dummy singleton class based on the Singleton metaclass.
    """
    value = None


def test_singleton_instance_is_unique():
    """
    Test that Singleton returns the same instance every time.
    """
    a = DummySingleton()
    a.value = 1
    b = DummySingleton()
    b.value = 2

    assert a is b
    assert a.value == b.value  # Both refer to the same instance


def test_singleton_value_persists():
    """
    Test that the value persists across multiple instantiations.
    """
    logger.debug("Creating new singleton instance with value 42")
    instance = DummySingleton()
    instance.value = 42
    assert instance.value == 42
    # Changing value should affect all references
    instance.value = 99
    another = DummySingleton()
    logger.error(another.value)
    assert another.value == 99


def test_singleton_instances_dict():
    """
    Test that the _instances dict contains only one instance.
    """
    # pylint: disable=protected-access
    DummySingleton()
    assert len(Singleton._instances) == 1
    assert DummySingleton in Singleton._instances
