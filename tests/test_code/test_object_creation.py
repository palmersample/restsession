"""
Basic object creation test - ensure each class can be instantiated as expected
"""
import logging
import pytest
import restsession.exceptions  # pylint: disable=import-error

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.code, pytest.mark.objects,]


def test_object_is_not_singleton(standard_test_class):
    """
    Create two instances of the test class and ensure they are different
    objects.

    :param standard_test_class: Fixture for standard test classes
    :return: None
    """
    object_one = standard_test_class()
    object_two = standard_test_class()

    assert object_one is not object_two


def test_object_is_singleton(singleton_test_class):
    """
    Create two instances of the test class and ensure they are the same
    objet reference.

    :param singleton_test_class: Fixture for singleton test classes
    :return: None
    """
    object_one = singleton_test_class()
    object_two = singleton_test_class()

    assert object_one is object_two


# pylint: disable=protected-access
def test_object_with_context_manager(test_class):
    """
    Test that context manager usage works as expected.

    :param test_class: Fixture for all test classes
    :return: None
    """
    with test_class() as class_instance:
        assert isinstance(class_instance, test_class)

        # Test the singleton has an instance defined
        if hasattr(class_instance.__class__, "_instances"):
            assert class_instance.__class__._instances != {}


def test_invalid_initialization(test_class):
    """
    Test that attempting to create an object with invalid attributes
    raises an InitializationError.

    :param test_class: Fixture for the class to test
    :param bad_session_attributes: Fixture with invalid attributes
    :return: None
    """
    with pytest.raises(restsession.exceptions.InitializationError):
        test_class(base_url=False)
