"""
Test functions for object attributes
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import warnings

import pytest
import restsession  # pylint: disable=import-error
import restsession.defaults  # pylint: disable=import-error
import restsession.exceptions  # pylint: disable=import-error

from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.code, pytest.mark.attrs,]


@pytest.fixture(scope="module", name="bad_session_attributes")
def fixture_bad_session_attributes():
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
        "base_url": False,
        "verify": 30,
        "max_reauth": "string_value",
        "redirect_header_hook": "No hook",
        "request_exception_hook": "No hook",
        "response_hooks": True
    }


def generic_response_hook():
    """
    Fixture for a generic response hook function. Just log a generic message.
    Used to test if the response hook can be set and cleared.

    :return: None
    """
    logger.debug("Generic response hook has been called!")
    return True


def test_valid_timeout(test_class):
    """
    Test that setting a valid timeout value is accepted by the class instance.

    :param test_class: Fixture of the class to test
    """
    with test_class() as class_instance:
        # Set a valid timeout value
        class_instance.timeout = 5.0

        # Check if the timeout attribute is set correctly
        assert class_instance.timeout == 5.0, \
            "Expected timeout to be set to 5.0"


def test_invalid_timeout(test_class):
    """
    Test that attempting to set an invalid timeout value results in an
    InvalidParameterError exception

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        with pytest.raises(restsession.exceptions.InvalidParameterError):
            class_instance.timeout = "Invalid string"


def test_valid_always_relative_url(test_class):
    """
    Test that setting a valid value for always_relative_url is accepted and
    correctly set.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        # Set the always_relative_url attribute to True
        class_instance.always_relative_url = True

        # Check if the attribute is set correctly
        assert class_instance.always_relative_url is True, \
            "Expected always_relative_url to be True"


def test_invalid_always_relative_url(test_class):
    """
    Test that setting an invalid value for always_relative_url raises
    InvalidParameterError.

    :param test_class: Fixture of the class to test
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.always_relative_url = 1234


def test_valid_safe_arguments(test_class):
    """
    Test that setting a valid value for safe_arguments is accepted and
    correctly set.

    :param test_class: Fixture of the class to test
    """
    with test_class() as class_instance:
        # Set the always_relative_url attribute to True
        class_instance.safe_arguments = True

        # Check if the attribute is set correctly
        assert class_instance.safe_arguments is True, \
            "Expected always_relative_url to be True"


def test_invalid_safe_arguments(test_class):
    """
    Test that setting an invalid value for safe_arguments raises
    InvalidParameterError.

    :param test_class: Fixture of the class to test
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.safe_arguments = "some string"


def test_base_url_validator(test_class):
    """
    Test that the base_url validator works correctly.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        # Set a valid base URL
        class_instance.base_url = "https://example.com/api"
        assert class_instance.base_url == "https://example.com/api/", \
            "Model validator did not append trailing slash to base_url"


def test_no_base_url(test_class):
    """
    Test that the base_url validator handles None correctly.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        # Set base URL to None
        assert class_instance.base_url is None, \
            "Base URL should be None when not set"


def test_base_url(test_class):
    """
    Test that the base_url validator appends a trailing slash if not present.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class(base_url="https://example.com/api") as class_instance:
        # Set a base URL without a trailing slash
        assert class_instance.base_url == "https://example.com/api/", \
            "Base URL did not have a trailing slash appended"


def test_good_status_codes(test_class):
    """
    Test that the retry_status_code_list validator accepts valid status codes.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retry_status_code_list = [200, 404, 500]  # Valid HTTP status codes
        assert class_instance.retry_status_code_list == [200, 404, 500], \
            "retry_status_code_list did not accept valid status codes"


def test_bad_status_codes(test_class):
    """
    Test that the retry_status_code_list validator raises an error for invalid status codes.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.retry_status_code_list = [999, 1000]  # Invalid HTTP status codes


def test_good_retry_delay(test_class):
    """
    Test that the backoff_factor accepts valid non-negative float values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retries = 2  # Valid non-negative int
        assert class_instance.retries == 2, \
            "Retry count did not accept valid non-negative integer value"


def test_bad_retry_delay(test_class):
    """
    Test that the backoff_factor raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.retries = -1.0  # Invalid negative int


def test_good_timeout(test_class):
    """
    Test that the timeout accepts valid non-negative float values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.timeout = 5.0  # Valid non-negative float
        assert class_instance.timeout == 5.0, \
            "Timeout did not accept valid non-negative float value"


def test_bad_timeout(test_class):
    """
    Test that the timeout raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.timeout = -1.0  # Invalid negative float


def test_good_max_redirects(test_class):
    """
    Test that the max_redirects accepts valid non-negative int values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.max_redirects = 3  # Valid non-negative int
        assert class_instance.max_redirects == 3, \
            "Max redirects did not accept valid non-negative integer value"


def test_bad_max_redirects(test_class):
    """
    Test that the max_redirects raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.max_redirects = -1  # Invalid negative int


def test_good_backoff_factor(test_class):
    """
    Test that the backoff_factor accepts valid non-negative float values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.backoff_factor = 0.5  # Valid non-negative float
        assert class_instance.backoff_factor == 0.5, \
            "Backoff factor did not accept valid non-negative float value"


def test_bad_backoff_factor(test_class):
    """
    Test that the backoff_factor raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.backoff_factor = -0.1  # Invalid negative float


def test_good_retry_method_list(test_class):
    """
    Test that the retry_method_list accepts valid list of HTTP methods.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retry_method_list = ["GET", "POST", "PUT"]  # Valid HTTP methods
        assert class_instance.retry_method_list == ["GET", "POST", "PUT"], \
            "retry_method_list did not accept valid list of HTTP methods"


def test_single_retry_method(test_class):
    """
    Test that the retry_method_list accepts a single valid HTTP method.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retry_method_list = "GET"  # Single valid HTTP method
        assert class_instance.retry_method_list == ["GET"], \
            "retry_method_list did not accept single valid HTTP method"


def test_bad_retry_method_list(test_class):
    """
    Test that the retry_method_list raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.retry_method_list = [None, False]  # Invalid HTTP methods


def test_good_retry_status_code_list(test_class):
    """
    Test that the retry_status_code_list accepts valid list of status codes.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.retry_status_code_list = [500, 502, 503]  # Valid HTTP status codes
        assert class_instance.retry_status_code_list == [500, 502, 503], \
            "retry_status_code_list did not accept valid list of status codes"


def test_bad_retry_status_code_list(test_class):
    """
    Test that the retry_status_code_list raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.retry_status_code_list = [999, 1000]  # Invalid HTTP status codes


def test_good_respect_retry_headers(test_class):
    """
    Test that the respect_retry_headers accepts a boolean value.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.respect_retry_headers = True  # Valid boolean
        assert class_instance.respect_retry_headers is True, \
            "respect_retry_headers did not accept valid boolean value"


def test_bad_respect_retry_headers(test_class):
    """
    Test that the respect_retry_headers raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.respect_retry_headers = "not_a_boolean"  # Invalid value


def test_good_base_url(test_class):
    """
    Test that the base_url accepts a valid URL string.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.base_url = "https://example.com/api/"  # Valid URL string
        assert class_instance.base_url == "https://example.com/api/", \
            "base_url did not accept valid URL string"


def test_bad_base_url(test_class):
    """
    Test that the base_url raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.base_url = 12345  # Invalid URL value


def test_good_verify(test_class):
    """
    Test that the verify accepts a boolean value.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.verify = True  # Valid boolean
        assert class_instance.verify is True, \
            "verify did not accept valid boolean value"


def test_bad_verify(test_class):
    """
    Test that the verify raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.verify = 12345  # Invalid value


def test_urllib3_warnings_disabled(test_class):
    """
    Test that urllib3 warnings are disabled by default.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.verify = False
        assert any(wf[2] is InsecureRequestWarning for wf in warnings.filters), \
            "InsecureRequestWarning should be in warnings filters when verify is False"


def test_valid_auth(test_class):
    """
    Test that the auth accepts a valid tuple of (username, password).

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.auth = ("username", "password")  # Valid auth tuple
        assert class_instance.auth == ("username", "password"), \
            "auth did not accept valid tuple of (username, password)"


def test_invalid_auth(test_class):
    """
    Test that the auth raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.auth = "not_a_tuple"  # Invalid auth value


def test_good_headers(test_class):
    """
    Test that the headers accepts a valid dictionary.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.headers = {"Content-Type": "application/json"}  # Valid headers dict
        assert class_instance.headers == {"Content-Type": "application/json"}, \
            "headers did not accept valid dictionary"


def test_bad_headers(test_class):
    """
    Test that the headers raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.headers = "not_a_dict"  # Invalid headers value


def test_headers_removed_on_redirect(test_class):
    """
    Test that headers are removed on redirect if specified.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.remove_headers_on_redirect = ["Authorization", "X-Custom-Header"]
        assert "Authorization" in class_instance.remove_headers_on_redirect, \
            "Expected 'Authorization' header to be in remove_headers_on_redirect"
        assert "X-Custom-Header" in class_instance.remove_headers_on_redirect, \
            "Expected 'X-Custom-Header' to be in remove_headers_on_redirect"


def test_invalid_remove_headers_on_redirect(test_class):
    """
    Test that setting remove_headers_on_redirect to an invalid type raises an error.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.remove_headers_on_redirect = True  # Invalid type


def test_good_max_reauth(test_class):
    """
    Test that the max_reauth accepts a valid non-negative integer.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.max_reauth = 3  # Valid non-negative integer
        assert class_instance.max_reauth == 3, \
            "max_reauth did not accept valid non-negative integer value"


def test_bad_max_reauth(test_class):
    """
    Test that the max_reauth raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.max_reauth = -1  # Invalid negative integer


def test_good_response_hooks(test_class):
    """
    Test that the response_hooks accepts a valid list of hooks.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.response_hooks = [generic_response_hook]

        assert isinstance(class_instance.response_hooks["response"][0], type(class_instance.redirect_header_hook)), \
            "Redirect header hook should be the first hook."

        assert isinstance(class_instance.response_hooks["response"][1], type(generic_response_hook)), \
            "Custom hook should be the second hook."

        assert isinstance(class_instance.response_hooks["response"][2], type(class_instance.request_exception_hook)), \
            "Request exception hook should be the third hook."


def test_bad_response_hooks(test_class):
    """
    Test that the response_hooks raises an error for invalid values.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with pytest.raises(restsession.exceptions.InvalidParameterError):
        with test_class() as class_instance:
            class_instance.response_hooks = "not_a_list"  # Invalid hooks value


def test_cleared_response_hooks(test_class):
    """
    Test that the response_hooks can be cleared.

    :param test_class: Fixture of the class to test
    :return: None
    """
    with test_class() as class_instance:
        class_instance.response_hooks = [generic_response_hook]  # Set initial hooks

        assert isinstance(class_instance.response_hooks["response"][1], type(generic_response_hook)), \
            "Custom hook should be the second hook."

        class_instance.clear_response_hooks()
        assert len(class_instance.response_hooks["response"]) == 2, \
            "Only 2 response hooks expected."

        assert isinstance(class_instance.response_hooks["response"][0], type(class_instance.redirect_header_hook)), \
            "Redirect header hook should be the first hook."

        assert isinstance(class_instance.response_hooks["response"][1], type(class_instance.request_exception_hook)), \
            "Request exception hook should be the third hook."


def test_reauth_count_initialization(test_class):
    """
    Test that reauth_count is initialized to 0 on object creation.
    """
    with test_class() as class_instance:
        assert class_instance.reauth_count == 0, \
            "reauth_count should be initialized to 0"
