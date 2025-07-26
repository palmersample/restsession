"""
Test cases for the InvalidParameterError class from restsession.exceptions.
"""
import logging
import pytest

from restsession.default_hooks import default_request_exception_hook  # pylint: disable=import-error
from restsession.exceptions import InvalidParameterError  # pylint: disable=import-error

from requests.models import Response
from requests.exceptions import (HTTPError,  # pylint: disable=redefined-builtin
                                 ConnectionError,
                                 InvalidJSONError,
                                 Timeout,
                                 MissingSchema,
                                 RetryError,
                                 TooManyRedirects,
                                 SSLError,
                                 RequestException,)


logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.code, pytest.mark.exceptions,]


@pytest.fixture(name="mock_response")
def fixture_mock_response(request):
    """
    Helper function to create a mock Response object.

    :param request: pytest request object, may contain a param for status_code
    :returns: a Response object with the specified status_code
    """
    try:
        status_code = request.param
    except AttributeError:
        status_code = 200

    response = Response()
    response.status_code = status_code
    yield response


class DummyPydanticError:  # pylint: disable=too-few-public-methods
    """
    Dummy class to simulate a Pydantic error object for testing.
    """
    def errors(self):
        """
        Simulate the errors method of a Pydantic error object.
        Returns a list of error dictionaries similar to what Pydantic would return.

        Used to test that the InvalidParameterError generated a formatted error message.
        """
        return [
            {
                "loc": ["field1"],
                "msg": "must be an integer",
                "type": "type_error.integer",
                "input": "abc"
            },
            {
                "loc": ["field2"],
                "msg": "value too small",
                "type": "value_error.number.not_ge",
                "input": -1
            }
        ]


def test_invalid_parameter_error_with_string():
    """
    Test InvalidParameterError initialized with a string message.
    """
    err = InvalidParameterError("Simple error message")
    assert "Simple error message" in str(err)


def test_invalid_parameter_error_with_pydantic_error():
    """
    Test InvalidParameterError initialized with a Pydantic-like error object.
    """
    err_obj = DummyPydanticError()
    err = InvalidParameterError(err_obj)
    assert "field1" in str(err)
    assert "must be an integer" in str(err)
    assert "field2" in str(err)
    assert "value too small" in str(err)


def test_invalid_parameter_error_with_empty_string():
    """Test InvalidParameterError with an empty string."""
    err = InvalidParameterError("")
    assert str(err) == ""


def test_invalid_parameter_error_with_non_error_object():
    """Test InvalidParameterError with a non-error object."""
    err = InvalidParameterError(123)
    assert "123" in str(err)


@pytest.mark.parametrize("mock_response", [400,], indirect=["mock_response"])
def test_default_request_exception_hook_http_error(mock_response):
    """
    Test that ``default_request_exception_hook`` raises HTTPError when the
    response status code is 400.

    :param mock_response: Fixture providing a mock Response object with status code 400
    """
    response = mock_response
    with pytest.raises(HTTPError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_connection_error(mock_response):
    """
    Test that ``default_request_exception_hook`` raises ConnectionError
    when the response simulates a connection error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(ConnectionError("Connection error"))
    with pytest.raises(ConnectionError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_invalid_json_error(mock_response):
    """
    Test that ``default_request_exception_hook`` raises InvalidJSONError when
    the response simulates an invalid JSON error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(InvalidJSONError("Invalid JSON"))
    with pytest.raises(InvalidJSONError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_timeout(mock_response):
    """
    Test that ``default_request_exception_hook`` raises Timeout when the
    response simulates a timeout error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(Timeout("Timeout error"))
    with pytest.raises(Timeout):
        default_request_exception_hook(response)


def test_default_request_exception_hook_missing_schema(mock_response):
    """
    Test that ``default_request_exception_hook`` raises MissingSchema when the
    response simulates a missing schema error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(MissingSchema("Missing schema"))
    with pytest.raises(MissingSchema):
        default_request_exception_hook(response)


def test_default_request_exception_hook_retry_error(mock_response):
    """
    Test that ``default_request_exception_hook`` raises RetryError when the
    response simulates a retry error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(RetryError("Retry error"))
    with pytest.raises(RetryError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_too_many_redirects(mock_response):
    """
    Test that ``default_request_exception_hook`` raises TooManyRedirects when
    the response simulates too many redirects.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(TooManyRedirects("Too many redirects"))
    with pytest.raises(TooManyRedirects):
        default_request_exception_hook(response)


def test_default_request_exception_hook_ssl_error(mock_response):
    """
    Test that ``default_request_exception_hook`` raises SSLError when the
    response simulates an SSL error.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(SSLError("SSL error"))
    with pytest.raises(SSLError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_generic_request_exception(mock_response):
    """
    Test that ``default_request_exception_hook`` raises RequestException when
    the response simulates a generic request exception.

    :param mock_response: Fixture providing a mock Response object
    """
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(RequestException("Generic request exception"))
    with pytest.raises(RequestException):
        default_request_exception_hook(response)


def test_default_request_exception_hook_no_exception(mock_response):
    """
    Test that ``default_request_exception_hook`` returns the response when no exceptions are raised.

    :param mock_response: Fixture providing a mock Response object
    :return: None
    """
    response = mock_response
    result = default_request_exception_hook(response)
    assert result is response
