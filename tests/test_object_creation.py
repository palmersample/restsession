"""
Basic object creation test - ensure each class can be instantiated as expected
"""
import logging
import pytest

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.objects


@pytest.fixture(scope="module")
def bad_session_attributes():
    """
    Fixture for invalid attributes for each session parameter.

    :return: dictionary with invalid attributes
    """
    return {
        "headers": ("value_one", "value_two", "value_three"),
        "auth_headers": 31337,
        "auth": {"key": "value"},
        "timeout": "string_value",
        "retries": "string_value",
        "max_redirects": [1, 3],
        "backoff_factor": ("tuple",),
        "retry_status_code_list": None,
        "retry_method_list": False,
        "respect_retry_headers": "Good question",
        "base_url": True,
        "verify": 30,
        "max_reauth": "string_value",
        "redirect_header_hook": "No hook",
        "request_exception_hook": "No hook",
        "response_hooks": True
    }


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
