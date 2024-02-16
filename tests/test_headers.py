"""
Test functions for request headers
"""
# pylint: disable=redefined-outer-name, line-too-long
import logging
import pytest
import requests_toolbelt.sessions
import restsession
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import requests.utils

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.headers


@pytest.fixture
def good_headers():
    """
    Fixture for good header values.

    :return: dict of header values
    """
    return {
        "User-Agent": "python-pytest",
        "Content-Type": "application/none",
        "Accept": "application/none",
        "Some-Header": "some-value"
    }


@pytest.fixture
def bad_headers():
    """
    Fixture for bad header value(s).

    :return: generic string
    """
    return "string_value"


@pytest.mark.parametrize("test_class, default_headers",
                         [(requests_toolbelt.sessions.BaseUrlSession, requests.utils.default_headers()),
                          (restsession.RestSession, restsession.defaults.SESSION_DEFAULTS["headers"]),
                          (restsession.RestSessionSingleton, restsession.defaults.SESSION_DEFAULTS["headers"])])
def test_default_headers(test_class, default_headers):
    """
    Test that instance headers are created and match the expected defaults.

    :param test_class: Fixture of the class to test
    :param default_headers: Fixture to return the expected default headers
    :return: None
    """
    with (test_class() as class_instance):
        logger.error("MRO: %s", type(class_instance).mro())
        assert class_instance.headers == default_headers, \
            f"Instance headers:\n{class_instance.headers}\nDefault headers:\n{default_headers}"


def test_good_headers(test_class, good_headers):
    """
    Test that setting headers to valid values is properly reflected in the
    class instance.

    :param test_class: Fixture of the class to test
    :param good_headers: Fixture of valid headers to set
    :return: None
    """
    with test_class() as class_instance:
        class_instance.headers = good_headers
        assert class_instance.headers == good_headers


@pytest.mark.parametrize("test_class",
                         [pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                       marks=pytest.mark.xfail(reason="Requests does not validate headers")),
                          restsession.RestSession,
                          restsession.RestSessionSingleton])
def test_bad_headers(test_class, bad_headers):
    """
    Test that assigning bad header(s) results in an InvalidParameterError
    exception

    :param test_class: Fixture of the class to test
    :param bad_headers: Fixture of invalid headers that should fail
    :return: None
    """
    with test_class() as class_instance:
        with pytest.raises(restsession.exceptions.InvalidParameterError):
            class_instance.headers = bad_headers


@pytest.mark.parametrize("request_method", ["get",
                                            "post",
                                            "put",
                                            "patch",
                                            "delete",
                                            "trace",
                                            "options"])
def test_get_headers(test_class, good_headers, request_method, generic_mock_server):
    """
    Test that explicitly-set headers are received and returned by the mock
    server.

    :param test_class: Fixture of the class to test
    :param good_headers: Fixture of valid headers to set
    :param request_method: Fixture of the HTTP verb to test
    :param generic_mock_server: Fixture for the generic mock server
    :return: None
    """
    with test_class() as class_instance:
        class_instance.headers = good_headers
        response = class_instance.request(request_method, generic_mock_server.url)
        received_headers = response.json().get("headers")
        logger.info("Expected headers:\n%s", good_headers)
        logger.info("Received headers:\n%s", received_headers)
        assert all(received_headers[k] == v for k, v in good_headers.items())
