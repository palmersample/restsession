"""
Testscript for combinations of request types (redirect and retry, retry
and redirect, various auth scenarios)
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
from .conftest import BaseHttpServer


logger = logging.getLogger(__name__)

pytestmark = pytest.mark.combinations


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
        logger.debug("Received request")
        logger.debug("MockServerRequestHandler headers: %s", self.headers)
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


class RedirectServerRequestHandler(MockServerRequestHandler):
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


class RetryServerRequestHandler(MockServerRequestHandler):
    """
    Handler definition for the generic HTTP request handler.

    Define actions for basic HTTP operations here.
    """
    # pylint: disable=invalid-name, useless-return
    max_retries = 0
    response_code = 429
    server_address = None
    request_count = 0
    retry_count = 0
    # 0 = No redirect. Otherwise, redirect after (n) requests to target
    redirect_after_requests = 0
    redirect_target = None

    def send_default_response(self):
        """
        Generic response for tests in this file. Return any received headers
        and body content as a JSON-encoded dictionary with key "headers"
        containing received headers and key "body" with received body.

        :return: None
        """
        self.__class__.request_count += 1
        self.__class__.retry_count += 1
        logger.info("Server received a request, returning 429")
        # self.send_header(
        #     "Content-Type", "application/json; charset=utf-8"
        # )

        if self.__class__.redirect_after_requests and self.__class__.request_count == self.__class__.redirect_after_requests:
            if self.__class__.redirect_target:
                logger.info("Sending redirect to %s", self.__class__.redirect_target)
                self.send_response(301)
                self.send_header("Location", self.__class__.redirect_target)
        elif self.__class__.request_count < self.__class__.max_retries:
            self.send_response(self.__class__.response_code)
            self.send_header("Retry-After", "1")
        else:
            self.send_response(200)
        self.end_headers()
        return


@pytest.fixture
def redirect_mock_server():
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
def retry_mock_server():
    """
    Start the mock server for incoming requests

    :return: BaseHttpServer instance with this test's request handler
    """
    # Max retries should just be something big. Can adjust for any test that
    # checks for a 200 after retry
    RetryServerRequestHandler.max_retries = 99
    RetryServerRequestHandler.request_count = 0
    RetryServerRequestHandler.response_code = 429
    RetryServerRequestHandler.retry_count = 0
    RetryServerRequestHandler.server_address = None
    RetryServerRequestHandler.redirect_after_requests = 0
    RetryServerRequestHandler.redirect_target = None

    return BaseHttpServer(handler=RetryServerRequestHandler)


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])
def test_redirect_then_retry(test_class, redirect_mock_server, retry_mock_server):
    RedirectServerRequestHandler.server_address = retry_mock_server.url
    RetryServerRequestHandler.max_retries = 2

    with test_class() as class_instance:
        request_response = class_instance.request("get", redirect_mock_server.url)
        redirect_mock_server.stop_server()
        retry_mock_server.stop_server()

        assert request_response.ok, \
            f"Expected a successful response, received {request_response.status_code}"


@pytest.mark.parametrize("test_class",
                         [
                             pytest.param(requests_toolbelt.sessions.BaseUrlSession,
                                          marks=pytest.mark.xfail(
                                          reason="Requests does not perform retries without an adapter mounted.")
                                          ),
                             restsession.RestSession,
                             restsession.RestSessionSingleton
                         ])

def test_retry_then_redirect(test_class, redirect_mock_server, retry_mock_server):
    RedirectServerRequestHandler.server_address = redirect_mock_server.url
    RedirectServerRequestHandler.max_redirects = 2
    RetryServerRequestHandler.redirect_after_requests = 2
    RetryServerRequestHandler.redirect_target = redirect_mock_server.url
    RetryServerRequestHandler.max_retries = 2

    with test_class() as class_instance:
        request_response = class_instance.request("get", retry_mock_server.url)
        redirect_mock_server.stop_server()
        retry_mock_server.stop_server()

        assert request_response.ok, \
            f"Expected a successful response, received {request_response.status_code}"
