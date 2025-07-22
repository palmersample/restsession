import logging
import pytest
from requests.models import Response
from requests.exceptions import (
    HTTPError, ConnectionError, InvalidJSONError, Timeout, MissingSchema,
    RetryError, TooManyRedirects, SSLError, RequestException
)
from restsession.default_hooks import default_request_exception_hook

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.exceptions


@pytest.fixture
def mock_response(request):
    """Helper function to create a mock Response object."""
    try:
        status_code = request.param
    except AttributeError:
        status_code = 200

    response = Response()
    response.status_code = status_code
    yield response


@pytest.mark.parametrize("mock_response", [400,], indirect=["mock_response"])
def test_default_request_exception_hook_http_error(mock_response):
    response = mock_response
    with pytest.raises(HTTPError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_connection_error(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(ConnectionError("Connection error"))
    with pytest.raises(ConnectionError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_invalid_json_error(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(InvalidJSONError("Invalid JSON"))
    with pytest.raises(InvalidJSONError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_timeout(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(Timeout("Timeout error"))
    with pytest.raises(Timeout):
        default_request_exception_hook(response)


def test_default_request_exception_hook_missing_schema(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(MissingSchema("Missing schema"))
    with pytest.raises(MissingSchema):
        default_request_exception_hook(response)


def test_default_request_exception_hook_retry_error(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(RetryError("Retry error"))
    with pytest.raises(RetryError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_too_many_redirects(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(TooManyRedirects("Too many redirects"))
    with pytest.raises(TooManyRedirects):
        default_request_exception_hook(response)


def test_default_request_exception_hook_ssl_error(mock_response):
    response = mock_response
    response.raise_for_status = lambda: (_ for _ in ()).throw(SSLError("SSL error"))
    with pytest.raises(SSLError):
        default_request_exception_hook(response)


def test_default_request_exception_hook_generic_request_exception(mock_response):
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