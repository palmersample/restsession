"""
Test functions for request headers
"""
# pylint: disable=redefined-outer-name, line-too-long
from http.server import BaseHTTPRequestHandler
import json
import logging
import pytest
import requests_toolbelt.sessions
import restsession
import restsession.defaults
import restsession.exceptions
import requests.exceptions
import requests.utils
from .conftest import BaseHttpServer


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.headers


class MockServerRequestHandler(BaseHTTPRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    server_address = None
    request_count = 0
    received_headers = None

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/json; charset=utf-8"
        )
        self.end_headers()
        response_data = {
            "headers": dict(self.headers),
            "body": {}
        }
        self.wfile.write(bytes(json.dumps(response_data).encode("utf-8")))

    def do_GET(self):
        """
        Handler for incoming GET requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_POST(self):
        """
        Handler for incoming POST requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_PUT(self):
        """
        Handler for incoming PUT requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_PATCH(self):
        """
        Handler for incoming PATCH requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_DELETE(self):
        """
        Handler for incoming DELETE requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_TRACE(self):
        """
        Handler for incoming TRACE requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

    def do_OPTIONS(self):
        """
        Handler for incoming OPTIONS requests.

        :return: self.send_default_response()
        """
        return self.send_default_response()

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


@pytest.fixture
def mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    return BaseHttpServer(handler=MockServerRequestHandler)


@pytest.mark.parametrize("test_class, default_headers",
                         [(requests_toolbelt.sessions.BaseUrlSession, requests.utils.default_headers()),
                          (restsession.RestSession, restsession.defaults.SESSION_DEFAULTS["headers"]),
                          (restsession.RestSessionSingleton, restsession.defaults.SESSION_DEFAULTS["headers"])])
def test_default_headers(test_class, default_headers):
    """

    :param test_class:
    :param default_headers:
    :return:
    """
    with test_class() as class_instance:
        assert class_instance.headers == default_headers


def test_good_headers(test_class, good_headers):
    """

    :param test_class:
    :param good_headers:
    :return:
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

    :param test_class:
    :param bad_headers:
    :return:
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
def test_get_headers(test_class, good_headers, request_method, mock_server):
    """

    :param test_class:
    :param good_headers:
    :param request_method:
    :param mock_server:
    :return:
    """
    with test_class() as class_instance:
        class_instance.headers = good_headers
        response = class_instance.request(request_method, mock_server.url)
        received_headers = response.json().get("headers")
        logger.info("Expected headers:\n%s", good_headers)
        logger.info("Received headers:\n%s", received_headers)
        assert all(received_headers[k] == v for k, v in good_headers.items())
