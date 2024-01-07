"""
Test functions for request redirects
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


pytestmark = pytest.mark.redirects

class RedirectServerRequestHandler(BaseHTTPRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    response_code = 301
    max_redirects = 0
    server_address = None
    request_count = 0
    redirect_count = 0

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        self.__class__.request_count += 1
        self.__class__.redirect_count += 1
        logger.info("Server received a request, returning redirect")
        # next_server = f"http://{self.__class__.server_address}"

        if self.__class__.request_count < self.__class__.max_redirects:
            self.send_response(self.__class__.response_code)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8"
            )
            self.send_header("Location", self.__class__.server_address)
        else:
            self.send_response(200)
        self.end_headers()
        return

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

    def do_HEAD(self):
        """
        Handler for incoming HEAD requests.

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
def mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    # Set max redirect to a high value so it's endless. Adjust for success
    # testing.
    RedirectServerRequestHandler.max_redirects = 99
    RedirectServerRequestHandler.request_count = 0
    RedirectServerRequestHandler.response_code = 301
    RedirectServerRequestHandler.redirect_count = 0
    RedirectServerRequestHandler.server_address = None
    return BaseHttpServer(handler=RedirectServerRequestHandler)


@pytest.fixture
def request_redirect_count():
    return 3


@pytest.fixture(params=["head",
                        "get",
                        "post",
                        "put",
                        "patch",
                        "delete",
                        "trace",
                        "options"])
def request_method(request):
    yield request.param


@pytest.fixture(params=[301, 302, 303, 307, 308])
def redirect_response_code(request):
    yield request.param


def test_successful_redirect(test_class, request_method, redirect_response_code, request_redirect_count, mock_server):

    # Expected redirect should be the configured redirect count, as a
    # 200 should be returned once the count is reached.
    RedirectServerRequestHandler.max_redirects = request_redirect_count
    RedirectServerRequestHandler.response_code = redirect_response_code
    RedirectServerRequestHandler.server_address = mock_server.url

    with test_class() as class_instance:
        class_instance.max_redirects = request_redirect_count
        logger.info(class_instance.max_redirects)

        request_response = class_instance.request(request_method, mock_server.url)
        mock_server.stop_server()

        assert RedirectServerRequestHandler.redirect_count == request_redirect_count, \
            f"Expected {request_redirect_count} retries, " \
            f"server received {RedirectServerRequestHandler.redirect_count}"

        assert request_response.ok, \
            f"Expected a successful response code, got: {request_response.status_code}"


def test_too_many_redirects(test_class, request_method, request_redirect_count, mock_server):

    # Expected redirect should be the configured redirect count + 1, as a
    # redirect should be sent until the end - no successful response will
    # be encountered.
    expected_redirect_count = request_redirect_count + 1
    RedirectServerRequestHandler.server_address = mock_server.url

    with test_class() as class_instance:
        class_instance.max_redirects = request_redirect_count

        with pytest.raises(requests.exceptions.TooManyRedirects) as exc_info:
            logger.debug("TooManyRedirects raised")
            class_instance.request(request_method, mock_server.url)

        mock_server.stop_server()

        assert RedirectServerRequestHandler.redirect_count == expected_redirect_count, \
            f"Expected {request_redirect_count} retries, " \
            f"server received {RedirectServerRequestHandler.redirect_count}"

        assert not 200 <= exc_info.value.response.status_code <= 299, \
            f"Expected a successful response code, got: {exc_info.value.response.status_code}"
